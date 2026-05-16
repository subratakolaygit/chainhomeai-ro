"""Tests for the algorithmic data quality detection module."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest
from config import RULES_CSV_PATH
from src.ingestion.data_quality import detect_data_quality
from src.tags.tag_registry import TagRegistry

_T0 = datetime(2022, 1, 1, tzinfo=UTC)

# Sensor benchmarks — kept local so tests are self-contained and readable.
_BM: dict[str, float] = {
    "ro1a_feed_press": 21.25,
    "ro1a_inlet_cond": 15332.683,
    "ro1a_inlet_flow": 24.6,
    "ro1a_inlet_orp": 1185.0,
    "ro1a_inlet_ph": 9.5,
    "ro1a_perm_cond": 133.25,
    "ro1a_perm_flow": 16.73,
    "ro1a_perm_ph": 8.97,
    "ro1a_reject_press": 14.9,
    "ro1a_reject_flow": 7.87,
    "ro1a_perm_press": 0.5,
    "ro1a_feed_temp": 25.0,
}


def _timestamps(n: int) -> list[datetime]:
    return [_T0 + timedelta(minutes=i) for i in range(n)]


def _clean_frame(n: int, sensor_overrides: dict[str, list] | None = None) -> pl.LazyFrame:
    """
    Build a minimal valid 23-column LazyFrame.

    All sensors oscillate ±0.1 % around benchmark — enough variation to avoid
    false stuck-value positives while staying well inside every normal range.
    """
    sensors = {col: [bm * (1.0 + 0.001 * ((-1) ** i)) for i in range(n)] for col, bm in _BM.items()}
    if sensor_overrides:
        sensors.update(sensor_overrides)

    return pl.DataFrame(
        {
            "timestamp": pl.Series(_timestamps(n), dtype=pl.Datetime("us", "UTC")),
            **{col: pl.Series(vals, dtype=pl.Float32) for col, vals in sensors.items()},
            "npd": pl.Series([0.8] * n, dtype=pl.Float32),
            "cip_cycle_number": pl.Series([1] * n, dtype=pl.UInt8),
            "hours_since_last_cip": pl.Series([0.0] * n, dtype=pl.Float32),
            "rul_hours": pl.Series([500.0] * n, dtype=pl.Float32),
            "failure_imminent": pl.Series([False] * n),
            "days_since_start": pl.Series([0.0] * n, dtype=pl.Float32),
            "data_quality_flag": pl.Series(["GOOD"] * n, dtype=pl.Categorical),
            "data_quality_issue_type": pl.Series([None] * n, dtype=pl.Categorical),
            "data_quality_affected_sensors": pl.Series([None] * n, dtype=pl.String),
            "data_quality_window_id": pl.Series([0] * n, dtype=pl.UInt16),
        }
    ).lazy()


@pytest.fixture(scope="module")
def registry() -> TagRegistry:
    return TagRegistry(RULES_CSV_PATH)


# ── Test 1 ────────────────────────────────────────────────────────────────────


def test_clean_frame_produces_no_flags(registry: TagRegistry) -> None:
    lf = _clean_frame(50)
    df = detect_data_quality(lf, registry, stuck_window=5).collect()
    assert (df["data_quality_flag"].cast(pl.String) == "GOOD").all()


# ── Test 2 ────────────────────────────────────────────────────────────────────


def test_returns_lazy_frame(registry: TagRegistry) -> None:
    result = detect_data_quality(_clean_frame(10), registry)
    assert isinstance(result, pl.LazyFrame)


# ── Test 3 ────────────────────────────────────────────────────────────────────


def test_extreme_spike_detected(registry: TagRegistry) -> None:
    n = 10
    # Row 5: feed_press = benchmark × 10 — far beyond any plausible spike threshold.
    press = [_BM["ro1a_feed_press"]] * n
    press[5] = _BM["ro1a_feed_press"] * 10.0
    lf = _clean_frame(n, {"ro1a_feed_press": press})
    df = detect_data_quality(lf, registry, stuck_window=3).collect()

    assert df["data_quality_flag"].cast(pl.String)[5] == "BAD"
    assert df["data_quality_issue_type"].cast(pl.String)[5] == "spike"
    assert "ro1a_feed_press" in (df["data_quality_affected_sensors"][5] or "")


# ── Test 4 ────────────────────────────────────────────────────────────────────


def test_out_of_range_detected_as_spike(registry: TagRegistry) -> None:
    # ro1a_feed_press normal range = (20.825, 21.675); benchmark = 21.25
    # half_range = 0.425; spike_threshold = 3 × 0.425 = 1.275
    # 19.0 → |19.0 − 21.25| = 2.25 > 1.275  ✓
    n = 10
    press = [_BM["ro1a_feed_press"]] * n
    press[3] = 19.0
    lf = _clean_frame(n, {"ro1a_feed_press": press})
    df = detect_data_quality(lf, registry, stuck_window=3).collect()

    assert df["data_quality_flag"].cast(pl.String)[3] == "BAD"
    assert df["data_quality_issue_type"].cast(pl.String)[3] == "spike"


# ── Test 5 ────────────────────────────────────────────────────────────────────


def test_stuck_value_detected(registry: TagRegistry) -> None:
    # Rows 0-29: inlet_ph constant at benchmark → rolling_std = 0 at row 29.
    n = 40
    ph = [_BM["ro1a_inlet_ph"]] * 30 + [_BM["ro1a_inlet_ph"] + 0.01 * i for i in range(n - 30)]
    lf = _clean_frame(n, {"ro1a_inlet_ph": ph})
    df = detect_data_quality(lf, registry, stuck_window=30).collect()

    stuck_rows = df.filter(pl.col("data_quality_flag").cast(pl.String) == "BAD")
    assert len(stuck_rows) > 0
    assert (stuck_rows["data_quality_issue_type"].cast(pl.String) == "stuck_value").all()


# ── Test 6 ────────────────────────────────────────────────────────────────────


def test_multi_sensor_spike_lists_all_affected(registry: TagRegistry) -> None:
    n = 10
    press = [_BM["ro1a_feed_press"]] * n
    cond = [_BM["ro1a_perm_cond"]] * n
    press[4] = 200.0  # spike
    cond[4] = 9999.0  # spike
    lf = _clean_frame(n, {"ro1a_feed_press": press, "ro1a_perm_cond": cond})
    df = detect_data_quality(lf, registry, stuck_window=3).collect()

    affected = df["data_quality_affected_sensors"][4] or ""
    assert "ro1a_feed_press" in affected
    assert "ro1a_perm_cond" in affected


# ── Test 7 ────────────────────────────────────────────────────────────────────


def test_existing_bad_rows_not_overwritten(registry: TagRegistry) -> None:
    n = 10
    flags = ["GOOD"] * n
    issues: list[str | None] = [None] * n
    affected: list[str | None] = [None] * n
    flags[2] = "BAD"
    issues[2] = "dropout"
    affected[2] = "ro1a_inlet_flow"

    df_base = pl.DataFrame(
        {
            "timestamp": pl.Series(_timestamps(n), dtype=pl.Datetime("us", "UTC")),
            **{
                col: pl.Series(
                    [bm * (1.0 + 0.001 * ((-1) ** i)) for i in range(n)],
                    dtype=pl.Float32,
                )
                for col, bm in _BM.items()
            },
            "npd": pl.Series([0.8] * n, dtype=pl.Float32),
            "cip_cycle_number": pl.Series([1] * n, dtype=pl.UInt8),
            "hours_since_last_cip": pl.Series([0.0] * n, dtype=pl.Float32),
            "rul_hours": pl.Series([500.0] * n, dtype=pl.Float32),
            "failure_imminent": pl.Series([False] * n),
            "days_since_start": pl.Series([0.0] * n, dtype=pl.Float32),
            "data_quality_flag": pl.Series(flags, dtype=pl.Categorical),
            "data_quality_issue_type": pl.Series(issues, dtype=pl.Categorical),
            "data_quality_affected_sensors": pl.Series(affected, dtype=pl.String),
            "data_quality_window_id": pl.Series([0] * n, dtype=pl.UInt16),
        }
    )
    df = detect_data_quality(df_base.lazy(), registry, stuck_window=3).collect()

    assert df["data_quality_flag"].cast(pl.String)[2] == "BAD"
    assert df["data_quality_issue_type"].cast(pl.String)[2] == "dropout"
    assert df["data_quality_affected_sensors"][2] == "ro1a_inlet_flow"


# ── Test 8 ────────────────────────────────────────────────────────────────────


def test_stuck_takes_priority_over_spike(registry: TagRegistry) -> None:
    # Rows 0-29: inlet_ph stuck. Row 29 also has a feed_press spike.
    # On that row: stuck_value must win over spike.
    n = 40
    ph = [_BM["ro1a_inlet_ph"]] * 30 + [_BM["ro1a_inlet_ph"] + 0.01 * i for i in range(n - 30)]
    press = [_BM["ro1a_feed_press"] * (1.0 + 0.001 * ((-1) ** i)) for i in range(n)]
    press[29] = 200.0  # extreme spike on the same row as the stuck window completion

    lf = _clean_frame(n, {"ro1a_inlet_ph": ph, "ro1a_feed_press": press})
    df = detect_data_quality(lf, registry, stuck_window=30).collect()

    assert df["data_quality_issue_type"].cast(pl.String)[29] == "stuck_value"
