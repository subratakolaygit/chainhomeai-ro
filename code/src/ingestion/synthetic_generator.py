"""4-year synthetic RO1A sensor dataset generator."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl
from config import (
    ALERT_AMBER_HOURS,
    BASE_NOISE_SIGMA,
    CIP_DURATION_MINUTES,
    CIP_INTERVAL_DAYS,
    DATASET_END_YEAR,
    DATASET_START_YEAR,
    FEED_PRESS_BENCHMARK,
    FEED_TEMP_AMPLITUDE,
    FEED_TEMP_BENCHMARK,
    INLET_COND_BENCHMARK,
    INLET_FLOW_BENCHMARK,
    INLET_ORP_BENCHMARK,
    INLET_PH_BENCHMARK,
    NOISE_SCALE_BY_YEAR,
    NPD_CIP_THRESHOLD,
    NPD_INITIAL,
    NPD_SLOPE_MULTIPLIER,
    PERM_COND_BENCHMARK,
    PERM_COND_DRIFT_PER_DAY,
    PERM_FLOW_BENCHMARK,
    PERM_PH_BENCHMARK,
    PERM_PRESS_BENCHMARK,
    POST_CIP_BASELINE_CREEP,
    RANDOM_SEED,
    REJECT_PRESS_BENCHMARK,
)

logger = logging.getLogger(__name__)

# All 12 sensor columns pipe-joined — written to affected_sensors during CIP
_ALL_SENSORS_STR: str = "|".join(
    [
        "ro1a_feed_press",
        "ro1a_inlet_cond",
        "ro1a_inlet_flow",
        "ro1a_inlet_orp",
        "ro1a_inlet_ph",
        "ro1a_perm_cond",
        "ro1a_perm_flow",
        "ro1a_perm_ph",
        "ro1a_reject_press",
        "ro1a_reject_flow",
        "ro1a_perm_press",
        "ro1a_feed_temp",
    ]
)

# CIP alkaline wash: pH rises, ORP drops, flows go to 0
_CIP_PH: float = 11.0
_CIP_ORP: float = -100.0

# microseconds from Unix epoch to 2022-01-01 00:00:00 UTC (dataset origin)
_ORIGIN_US: int = int(np.datetime64("2022-01-01T00:00:00", "us").astype(np.int64))


class SyntheticRO1AGenerator:
    """
    Generates the 4-year RO1A sensor dataset with realistic membrane degradation.

    Year 1 (2022): new membrane, CIP every 90 days.
    Year 2 (2023): early aging, CIP every 70 days.
    Year 3 (2024): mid-life, CIP every 50 days.
    Year 4 (2025): end-of-life, CIP every 35 days. Test set (held out).
    """

    # Base fouling slope: NPD rises from NPD_INITIAL to NPD_CIP_THRESHOLD
    # across one Year-1 inter-CIP interval.
    _BASE_SLOPE: float = (NPD_CIP_THRESHOLD - NPD_INITIAL) / (CIP_INTERVAL_DAYS[2022] * 24.0)

    def __init__(self, output_dir: Path) -> None:
        """
        Args:
            output_dir: Root directory for year-partitioned Parquet output.
        """
        self._output_dir = output_dir
        self._rng = np.random.default_rng(seed=RANDOM_SEED)

    def generate_all(self) -> None:
        """Generate all 4 years and write year-partitioned Parquet files."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        for year in range(DATASET_START_YEAR, DATASET_END_YEAR + 1):
            logger.info("Generating year %d ...", year)
            df = self._generate_year(year)
            year_dir = self._output_dir / f"year={year}"
            year_dir.mkdir(exist_ok=True)
            out_path = year_dir / "ro1a_synthetic.parquet"
            df.write_parquet(out_path)
            logger.info("  %d rows → %s", len(df), out_path)

    # ------------------------------------------------------------------
    # Year generation
    # ------------------------------------------------------------------

    def _generate_year(self, year: int) -> pl.DataFrame:
        """Build the full 23-column DataFrame for one calendar year."""
        timestamps = pl.datetime_range(
            datetime(year, 1, 1, tzinfo=UTC),
            datetime(year, 12, 31, 23, 59, tzinfo=UTC),
            interval="1m",
            time_unit="us",
            time_zone="UTC",
            eager=True,
        )
        n = len(timestamps)
        ts_us = timestamps.to_numpy().astype(np.int64)  # µs since Unix epoch

        # Fractional day of year (0.0 = Jan 1 00:00)
        year_origin_us = int(np.datetime64(f"{year}-01-01T00:00:00", "us").astype(np.int64))
        day_of_year = (ts_us - year_origin_us) / (24 * 60 * 60 * 1_000_000)

        cip_events = self._build_cip_schedule(year, n)
        cip_cycle_num, hours_since_cip, rul_hours, is_cip = self._compute_time_features(
            n, cip_events
        )

        noise = NOISE_SCALE_BY_YEAR[year]
        npd_base = NPD_INITIAL * (1.0 + POST_CIP_BASELINE_CREEP[year])
        slope = self._BASE_SLOPE * NPD_SLOPE_MULTIPLIER[year]

        # NPD — primary membrane health KPI
        npd = (
            npd_base
            + slope * hours_since_cip
            + self._rng.normal(0.0, BASE_NOISE_SIGMA["npd"] * noise, n)
        ).astype(np.float32)
        npd[is_cip] = 0.0

        # Fractional NPD deviation drives correlated sensor shifts
        npd_dev = np.where(is_cip, 0.0, (npd - NPD_INITIAL) / NPD_INITIAL)

        feed_press = (
            FEED_PRESS_BENCHMARK * (1.0 + 0.04 * npd_dev)
            + self._rng.normal(0.0, BASE_NOISE_SIGMA["ro1a_feed_press"] * noise, n)
        ).astype(np.float32)

        inlet_flow = (
            INLET_FLOW_BENCHMARK
            + self._rng.normal(0.0, BASE_NOISE_SIGMA["ro1a_inlet_flow"] * noise, n)
        ).astype(np.float32)

        perm_flow = (
            PERM_FLOW_BENCHMARK * (1.0 - 0.03 * npd_dev)
            + self._rng.normal(0.0, BASE_NOISE_SIGMA["ro1a_perm_flow"] * noise, n)
        ).astype(np.float32)

        # Mass-balance approximation: reject = inlet - permeate
        reject_flow = (
            inlet_flow
            - perm_flow
            + self._rng.normal(0.0, BASE_NOISE_SIGMA["ro1a_reject_flow"] * noise, n)
        ).astype(np.float32)

        perm_press = (
            PERM_PRESS_BENCHMARK
            + self._rng.normal(0.0, BASE_NOISE_SIGMA["ro1a_perm_press"] * noise, n)
        ).astype(np.float32)

        reject_press = (
            REJECT_PRESS_BENCHMARK
            + self._rng.normal(0.0, BASE_NOISE_SIGMA["ro1a_reject_press"] * noise, n)
        ).astype(np.float32)

        # Seasonal temperature — cooler in winter, warmer in summer
        feed_temp = (
            FEED_TEMP_BENCHMARK
            + FEED_TEMP_AMPLITUDE * np.sin(2.0 * np.pi * day_of_year / 365.25 - np.pi / 2.0)
            + self._rng.normal(0.0, BASE_NOISE_SIGMA["ro1a_feed_temp"] * noise, n)
        ).astype(np.float32)

        # Independent feed-quality sensors (slow Brownian walk — day-to-day variation)
        inlet_cond = self._random_walk(
            n,
            INLET_COND_BENCHMARK,
            50.0 * noise,
            BASE_NOISE_SIGMA["ro1a_inlet_cond"] * noise,
            (12_000.0, 18_000.0),
        )
        inlet_orp = self._random_walk(
            n,
            INLET_ORP_BENCHMARK,
            5.0 * noise,
            BASE_NOISE_SIGMA["ro1a_inlet_orp"] * noise,
            (900.0, 1_400.0),
        )
        inlet_ph = self._random_walk(
            n,
            INLET_PH_BENCHMARK,
            0.002 * noise,
            BASE_NOISE_SIGMA["ro1a_inlet_ph"] * noise,
            (8.5, 10.5),
        )

        # Permeate conductivity — slow aging drift (salt rejection degrades)
        perm_cond = (
            PERM_COND_BENCHMARK
            + PERM_COND_DRIFT_PER_DAY[year] * day_of_year
            + self._rng.normal(0.0, BASE_NOISE_SIGMA["ro1a_perm_cond"] * noise, n)
        ).astype(np.float32)

        perm_ph = self._random_walk(
            n,
            PERM_PH_BENCHMARK,
            0.001 * noise,
            0.01 * noise,
            (8.0, 10.0),
        )

        # Apply CIP state — flows/pressures/cond go to 0, pH/ORP go chemically abnormal
        for arr in (
            feed_press,
            inlet_flow,
            perm_flow,
            reject_flow,
            perm_press,
            reject_press,
            perm_cond,
            inlet_cond,
        ):
            arr[is_cip] = 0.0
        inlet_ph[is_cip] = _CIP_PH
        inlet_orp[is_cip] = _CIP_ORP
        perm_ph[is_cip] = _CIP_PH - 0.5

        # Data quality columns — GOOD everywhere except CIP windows (UNCERTAIN)
        quality_flags: list[str] = ["UNCERTAIN" if v else "GOOD" for v in is_cip]
        issue_types: list[str | None] = ["cip_active" if v else None for v in is_cip]
        affected: list[str | None] = [_ALL_SENSORS_STR if v else None for v in is_cip]

        # Global time index from 2022-01-01 (used as long-run aging feature)
        days_since_start = ((ts_us - _ORIGIN_US) / (24 * 60 * 60 * 1_000_000)).astype(np.float32)

        return pl.DataFrame(
            {
                "timestamp": timestamps,
                "ro1a_feed_press": feed_press,
                "ro1a_inlet_cond": inlet_cond,
                "ro1a_inlet_flow": inlet_flow,
                "ro1a_inlet_orp": inlet_orp,
                "ro1a_inlet_ph": inlet_ph,
                "ro1a_perm_cond": perm_cond,
                "ro1a_perm_flow": perm_flow,
                "ro1a_perm_ph": perm_ph,
                "ro1a_reject_press": reject_press,
                "ro1a_reject_flow": reject_flow,
                "ro1a_perm_press": perm_press,
                "ro1a_feed_temp": feed_temp,
                "npd": npd,
                "cip_cycle_number": pl.Series("cip_cycle_number", cip_cycle_num, dtype=pl.UInt8),
                "hours_since_last_cip": hours_since_cip,
                "rul_hours": rul_hours,
                "failure_imminent": (rul_hours <= ALERT_AMBER_HOURS) & ~is_cip,
                "days_since_start": days_since_start,
                "data_quality_flag": pl.Series(
                    "data_quality_flag", quality_flags, dtype=pl.Categorical
                ),
                "data_quality_issue_type": pl.Series(
                    "data_quality_issue_type", issue_types, dtype=pl.Categorical
                ),
                "data_quality_affected_sensors": pl.Series(
                    "data_quality_affected_sensors", affected, dtype=pl.String
                ),
                "data_quality_window_id": pl.Series(
                    "data_quality_window_id",
                    np.zeros(n, dtype=np.uint16),
                    dtype=pl.UInt16,
                ),
            }
        )

    # ------------------------------------------------------------------
    # CIP schedule
    # ------------------------------------------------------------------

    def _build_cip_schedule(self, year: int, n_minutes: int) -> list[tuple[int, int]]:
        """
        Compute CIP event positions for the year.

        Args:
            year: Calendar year.
            n_minutes: Total minutes in the year.

        Returns:
            List of (start_minute_index, end_minute_index) for each CIP.
        """
        interval = int(CIP_INTERVAL_DAYS[year] * 24 * 60)
        duration = CIP_DURATION_MINUTES
        events: list[tuple[int, int]] = []
        next_start = interval

        while next_start + duration < n_minutes:
            jitter = int(self._rng.integers(-2 * 24 * 60, 2 * 24 * 60))
            cip_start = max(duration, next_start + jitter)
            cip_end = min(n_minutes, cip_start + duration)
            events.append((cip_start, cip_end))
            next_start = cip_end + interval

        return events

    # ------------------------------------------------------------------
    # Time feature computation
    # ------------------------------------------------------------------

    def _compute_time_features(
        self,
        n: int,
        cip_events: list[tuple[int, int]],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Derive time-based columns from the CIP schedule.

        Args:
            n: Total minute count in the year.
            cip_events: List of (start_idx, end_idx) CIP windows.

        Returns:
            Tuple of (cip_cycle_num, hours_since_cip, rul_hours, is_cip),
            each a numpy array of length n.
        """
        idx = np.arange(n, dtype=np.int32)

        # Boolean mask: True for every minute inside a CIP window
        is_cip = np.zeros(n, dtype=bool)
        for s, e in cip_events:
            is_cip[s:e] = True

        if not cip_events:
            hours_since_cip = (idx / 60.0).astype(np.float32)
            rul_hours = ((n - 1 - idx) / 60.0).astype(np.float32)
            return np.zeros(n, dtype=np.uint8), hours_since_cip, rul_hours, is_cip

        starts = np.array([s for s, _ in cip_events], dtype=np.int32)
        ends = np.array([e for _, e in cip_events], dtype=np.int32)

        # cip_cycle_num: how many CIPs have fully completed before this minute
        cip_cycle_num = np.searchsorted(ends, idx, side="right").astype(np.uint8)

        # hours_since_last_cip: minutes since last CIP completion ÷ 60
        hours_since_cip = np.empty(n, dtype=np.float32)
        for cycle in range(len(ends) + 1):
            mask = cip_cycle_num == cycle
            if not mask.any():
                continue
            last_end = ends[cycle - 1] if cycle > 0 else 0
            hours_since_cip[mask] = (idx[mask] - last_end) / 60.0
        hours_since_cip[is_cip] = 0.0

        # rul_hours: minutes until next CIP start ÷ 60 (0 during CIP)
        next_start_idx = np.searchsorted(starts, idx, side="right")
        in_bounds = next_start_idx < len(starts)
        rul_hours = np.empty(n, dtype=np.float32)
        rul_hours[in_bounds] = (starts[next_start_idx[in_bounds]] - idx[in_bounds]) / 60.0
        beyond = ~in_bounds
        rul_hours[beyond] = (n - 1 - idx[beyond]) / 60.0
        rul_hours[is_cip] = 0.0

        return cip_cycle_num, hours_since_cip, rul_hours, is_cip

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _random_walk(
        self,
        n: int,
        start: float,
        step_sigma: float,
        noise_sigma: float,
        bounds: tuple[float, float],
    ) -> np.ndarray:
        """
        Brownian-motion random walk centred at start, clipped to bounds.

        Args:
            n: Array length.
            start: Starting (and approximate mean) value.
            step_sigma: Std-dev of each incremental step.
            noise_sigma: Additional i.i.d. measurement noise std-dev.
            bounds: (min, max) hard clip limits.

        Returns:
            Float32 numpy array of length n.
        """
        walk = np.cumsum(self._rng.normal(0.0, step_sigma, n))
        walk = walk - walk[0] + start  # anchor to start
        walk += self._rng.normal(0.0, noise_sigma, n)
        return np.clip(walk, bounds[0], bounds[1]).astype(np.float32)
