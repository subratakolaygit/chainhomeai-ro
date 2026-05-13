"""Injects synthetic bad-sensor windows into a generated year DataFrame."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl
from config import BAD_WINDOWS_PER_YEAR, BASE_NOISE_SIGMA, NOISE_SCALE_BY_YEAR, RANDOM_SEED

logger = logging.getLogger(__name__)

# Sensors eligible for each fault type
_ELIGIBLE: dict[str, list[str]] = {
    "dropout": ["ro1a_inlet_flow", "ro1a_feed_press", "ro1a_perm_flow", "ro1a_perm_cond"],
    "stuck_value": ["ro1a_inlet_ph", "ro1a_inlet_orp", "ro1a_inlet_cond", "ro1a_perm_cond"],
    "spike": [
        "ro1a_feed_press", "ro1a_inlet_flow", "ro1a_perm_flow",
        "ro1a_reject_press", "ro1a_perm_cond", "ro1a_inlet_ph",
    ],
    "calibration_drift": ["ro1a_perm_cond", "ro1a_inlet_ph"],
    "noise_burst": ["ro1a_reject_press", "ro1a_inlet_flow", "ro1a_perm_flow"],
}

# Duration range (minutes) per fault type
_DURATION_RANGE: dict[str, tuple[int, int]] = {
    "dropout": (30, 240),
    "stuck_value": (60, 480),
    "spike": (1, 5),
    "calibration_drift": (7 * 24 * 60, 28 * 24 * 60),  # 1–4 weeks
    "noise_burst": (120, 720),
}

# Severity: 1=minor, 2=significant, 3=critical
_SEVERITY: dict[str, int] = {
    "dropout": 3,
    "stuck_value": 2,
    "calibration_drift": 2,
    "noise_burst": 1,
    "spike": 3,
}


@dataclass
class _WindowRecord:
    window_id: int
    sensor_name: str
    window_start: datetime
    window_end: datetime
    issue_type: str
    severity: int
    injected: bool = True


@dataclass
class BadWindowInjector:
    """
    Reads a year's DataFrame, injects bad-sensor windows, returns modified
    DataFrame and registry rows.

    Uses a separate RNG seeded at RANDOM_SEED + 100 so injection is
    independent of the generator's random stream.
    """

    _rng: np.random.Generator = field(init=False)
    _next_window_id: int = field(init=False)

    def __init__(self, starting_window_id: int = 1) -> None:
        """
        Args:
            starting_window_id: First window_id value to assign (increments across years).
        """
        self._rng = np.random.default_rng(seed=RANDOM_SEED + 100)
        self._next_window_id = starting_window_id

    def inject(
        self, df: pl.DataFrame, year: int
    ) -> tuple[pl.DataFrame, list[dict]]:
        """
        Inject bad windows into df for the given year.

        Args:
            df: Clean DataFrame from SyntheticRO1AGenerator.
            year: Calendar year (used to determine window counts and noise scale).

        Returns:
            Tuple of (modified DataFrame, list of registry row dicts).
        """
        counts = BAD_WINDOWS_PER_YEAR[year]
        n = len(df)
        noise = NOISE_SCALE_BY_YEAR[year]

        # Mutable copies of quality columns
        flag_list: list[str] = df["data_quality_flag"].cast(pl.String).to_list()
        issue_list: list[str | None] = df["data_quality_issue_type"].cast(pl.String).to_list()
        affected_list: list[str | None] = df["data_quality_affected_sensors"].to_list()
        wid_list: list[int] = df["data_quality_window_id"].to_list()

        # Mutable sensor value columns (float32 numpy)
        sensor_arrays: dict[str, np.ndarray] = {
            col: df[col].to_numpy(zero_copy_only=False).copy()
            for col in df.columns
            if df[col].dtype == pl.Float32
        }

        registry: list[dict] = []
        timestamps = df["timestamp"]

        for issue_type, count in counts.items():
            if count == 0:
                continue
            eligible = _ELIGIBLE[issue_type]
            dur_min, dur_max = _DURATION_RANGE[issue_type]

            for _ in range(count):
                sensor = eligible[int(self._rng.integers(0, len(eligible)))]
                duration = int(self._rng.integers(dur_min, dur_max + 1))

                # Pick a start that avoids existing BAD/UNCERTAIN rows and fits in year
                start_idx = self._pick_start(flag_list, n, duration)
                if start_idx is None:
                    logger.warning(
                        "Could not place %s window for %s in %d", issue_type, sensor, year
                    )
                    continue

                end_idx = min(n, start_idx + duration)
                wid = self._next_window_id
                self._next_window_id += 1

                # Modify sensor values
                arr = sensor_arrays[sensor]
                self._apply_fault(arr, issue_type, start_idx, end_idx, sensor, noise)

                # Update quality columns
                for i in range(start_idx, end_idx):
                    if flag_list[i] == "GOOD":
                        flag_list[i] = "BAD"
                        issue_list[i] = issue_type
                        affected_list[i] = sensor
                        wid_list[i] = wid

                ts_start: datetime = timestamps[start_idx]
                ts_end: datetime = timestamps[end_idx - 1]
                registry.append(
                    _WindowRecord(
                        window_id=wid,
                        sensor_name=sensor,
                        window_start=ts_start,
                        window_end=ts_end,
                        issue_type=issue_type,
                        severity=_SEVERITY[issue_type],
                    ).__dict__
                )
                logger.debug(
                    "  Injected %s on %s [%d:%d] wid=%d",
                    issue_type, sensor, start_idx, end_idx, wid
                )

        # Rebuild modified DataFrame columns
        updated: dict[str, pl.Series] = {}
        for col, arr in sensor_arrays.items():
            updated[col] = pl.Series(col, arr, dtype=pl.Float32)

        updated["data_quality_flag"] = pl.Series(
            "data_quality_flag", flag_list, dtype=pl.Categorical
        )
        updated["data_quality_issue_type"] = pl.Series(
            "data_quality_issue_type", issue_list, dtype=pl.Categorical
        )
        updated["data_quality_affected_sensors"] = pl.Series(
            "data_quality_affected_sensors", affected_list, dtype=pl.String
        )
        updated["data_quality_window_id"] = pl.Series(
            "data_quality_window_id", wid_list, dtype=pl.UInt16
        )

        modified = df.with_columns([s.alias(s.name) for s in updated.values()])
        return modified, registry

    # ------------------------------------------------------------------
    # Fault application
    # ------------------------------------------------------------------

    def _apply_fault(
        self,
        arr: np.ndarray,
        issue_type: str,
        start: int,
        end: int,
        sensor: str,
        noise_scale: float,
    ) -> None:
        """Modify arr in-place for the specified fault window."""
        if issue_type == "dropout":
            arr[start:end] = np.nan

        elif issue_type == "stuck_value":
            arr[start:end] = float(arr[start])

        elif issue_type == "spike":
            # Single extreme reading at window start
            arr[start] = float(arr[start]) * 5.0

        elif issue_type == "calibration_drift":
            # Linear drift over the window duration
            n_pts = end - start
            drift = np.linspace(0.0, 0.5 * noise_scale, n_pts, dtype=np.float32)
            arr[start:end] = arr[start:end] + drift

        elif issue_type == "noise_burst":
            burst_sigma = BASE_NOISE_SIGMA.get(sensor, 0.05) * noise_scale * 8.0
            arr[start:end] += self._rng.normal(0.0, burst_sigma, end - start).astype(np.float32)

    def _pick_start(
        self, flag_list: list[str], n: int, duration: int
    ) -> int | None:
        """
        Find a random start index where the window does not overlap existing
        BAD or UNCERTAIN rows. Returns None after 20 failed attempts.
        """
        for _ in range(20):
            candidate = int(self._rng.integers(0, max(1, n - duration)))
            window_flags = flag_list[candidate: candidate + duration]
            if all(f == "GOOD" for f in window_flags):
                return candidate
        return None


def write_bad_windows_registry(registry_rows: list[dict], out_path: Path) -> None:
    """
    Write the accumulated bad-window registry to Parquet.

    Args:
        registry_rows: List of dicts from BadWindowInjector.inject().
        out_path: Destination Parquet path.
    """
    if not registry_rows:
        logger.warning("No bad windows to write — registry will be empty.")

    df = pl.DataFrame(
        {
            "window_id": pl.Series([r["window_id"] for r in registry_rows], dtype=pl.UInt16),
            "sensor_name": pl.Series([r["sensor_name"] for r in registry_rows], dtype=pl.String),
            "window_start": pl.Series(
                [r["window_start"] for r in registry_rows], dtype=pl.Datetime("us", "UTC")
            ),
            "window_end": pl.Series(
                [r["window_end"] for r in registry_rows], dtype=pl.Datetime("us", "UTC")
            ),
            "issue_type": pl.Series(
                [r["issue_type"] for r in registry_rows], dtype=pl.Categorical
            ),
            "severity": pl.Series([r["severity"] for r in registry_rows], dtype=pl.UInt8),
            "injected": pl.Series([r["injected"] for r in registry_rows], dtype=pl.Boolean),
        }
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(out_path)
    logger.info("Bad-windows registry written: %d rows → %s", len(df), out_path)
