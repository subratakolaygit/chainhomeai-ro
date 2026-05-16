"""Tests for SensorFrameSchema validation."""

from __future__ import annotations

from datetime import UTC

import polars as pl
import pytest
from src.ingestion.exceptions import DataIngestionError
from src.ingestion.schema import EXPECTED_SCHEMA, SensorFrameSchema


def _make_valid_frame() -> pl.LazyFrame:
    """Minimal 3-row DataFrame with the correct 23-column schema."""
    n = 3
    from datetime import datetime

    data: dict = {
        "timestamp": pl.datetime_range(
            datetime(2022, 1, 1, tzinfo=UTC),
            datetime(2022, 1, 1, 0, 2, tzinfo=UTC),
            interval="1m",
            time_unit="us",
            time_zone="UTC",
            eager=True,
        ),
        "ro1a_feed_press": pl.Series([21.25] * n, dtype=pl.Float32),
        "ro1a_inlet_cond": pl.Series([15332.0] * n, dtype=pl.Float32),
        "ro1a_inlet_flow": pl.Series([24.6] * n, dtype=pl.Float32),
        "ro1a_inlet_orp": pl.Series([1185.0] * n, dtype=pl.Float32),
        "ro1a_inlet_ph": pl.Series([9.5] * n, dtype=pl.Float32),
        "ro1a_perm_cond": pl.Series([133.25] * n, dtype=pl.Float32),
        "ro1a_perm_flow": pl.Series([16.73] * n, dtype=pl.Float32),
        "ro1a_perm_ph": pl.Series([8.97] * n, dtype=pl.Float32),
        "ro1a_reject_press": pl.Series([14.9] * n, dtype=pl.Float32),
        "ro1a_reject_flow": pl.Series([7.87] * n, dtype=pl.Float32),
        "ro1a_perm_press": pl.Series([0.5] * n, dtype=pl.Float32),
        "ro1a_feed_temp": pl.Series([25.0] * n, dtype=pl.Float32),
        "npd": pl.Series([0.843] * n, dtype=pl.Float32),
        "cip_cycle_number": pl.Series([0] * n, dtype=pl.UInt8),
        "hours_since_last_cip": pl.Series([0.0] * n, dtype=pl.Float32),
        "rul_hours": pl.Series([100.0] * n, dtype=pl.Float32),
        "failure_imminent": pl.Series([False] * n, dtype=pl.Boolean),
        "days_since_start": pl.Series([0.0] * n, dtype=pl.Float32),
        "data_quality_flag": pl.Series(["GOOD"] * n, dtype=pl.Categorical),
        "data_quality_issue_type": pl.Series([None] * n, dtype=pl.Categorical),
        "data_quality_affected_sensors": pl.Series([None] * n, dtype=pl.String),
        "data_quality_window_id": pl.Series([0] * n, dtype=pl.UInt16),
    }
    return pl.DataFrame(data).lazy()


def test_valid_frame_passes() -> None:
    SensorFrameSchema.validate(_make_valid_frame())  # must not raise


def test_missing_column_raises() -> None:
    lf = _make_valid_frame().drop("ro1a_feed_press")
    with pytest.raises(DataIngestionError, match="ro1a_feed_press"):
        SensorFrameSchema.validate(lf)


def test_wrong_dtype_raises() -> None:
    lf = _make_valid_frame().with_columns(pl.col("ro1a_feed_press").cast(pl.Float64))
    with pytest.raises(DataIngestionError, match="ro1a_feed_press"):
        SensorFrameSchema.validate(lf)


def test_extra_column_strict_raises() -> None:
    lf = _make_valid_frame().with_columns(pl.lit(1).alias("extra_col"))
    with pytest.raises(DataIngestionError, match="extra_col"):
        SensorFrameSchema.validate(lf, strict=True)


def test_extra_column_nonstrict_passes() -> None:
    lf = _make_valid_frame().with_columns(pl.lit(1).alias("extra_col"))
    SensorFrameSchema.validate(lf, strict=False)  # must not raise


def test_expected_schema_has_23_columns() -> None:
    assert len(EXPECTED_SCHEMA) == 23
