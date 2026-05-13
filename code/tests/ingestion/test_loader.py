"""Tests for ingest_synthetic_data and load_bad_windows_registry."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pytest
from src.ingestion.exceptions import DataIngestionError
from src.ingestion.loader import ingest_synthetic_data, load_bad_windows_registry
from src.ingestion.schema import EXPECTED_SCHEMA


def _write_mini_parquet(directory: Path) -> Path:
    """Write a 3-row valid Parquet fixture to directory/year=2022/ro1a_synthetic.parquet."""
    n = 3
    year_dir = directory / "year=2022"
    year_dir.mkdir(parents=True)
    out = year_dir / "ro1a_synthetic.parquet"

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
    pl.DataFrame(data).write_parquet(out)
    return directory


def _write_mini_registry(path: Path) -> None:
    """Write a minimal bad-windows registry Parquet."""
    pl.DataFrame(
        {
            "window_id": pl.Series([1], dtype=pl.UInt16),
            "sensor_name": pl.Series(["ro1a_feed_press"], dtype=pl.String),
            "window_start": pl.Series(
                [datetime(2022, 3, 1, tzinfo=UTC)], dtype=pl.Datetime("us", "UTC")
            ),
            "window_end": pl.Series(
                [datetime(2022, 3, 1, 2, 0, tzinfo=UTC)], dtype=pl.Datetime("us", "UTC")
            ),
            "issue_type": pl.Series(["dropout"], dtype=pl.Categorical),
            "severity": pl.Series([3], dtype=pl.UInt8),
            "injected": pl.Series([True], dtype=pl.Boolean),
        }
    ).write_parquet(path)


# ------------------------------------------------------------------
# ingest_synthetic_data
# ------------------------------------------------------------------

def test_returns_lazyframe(tmp_path: Path) -> None:
    data_dir = _write_mini_parquet(tmp_path)
    result = ingest_synthetic_data(data_dir)
    assert isinstance(result, pl.LazyFrame)


def test_schema_matches_expected(tmp_path: Path) -> None:
    data_dir = _write_mini_parquet(tmp_path)
    lf = ingest_synthetic_data(data_dir)
    schema = lf.collect_schema()
    for col, dtype in EXPECTED_SCHEMA.items():
        assert col in schema, f"Missing column: {col}"
        assert schema[col] == dtype, f"{col}: expected {dtype}, got {schema[col]}"


def test_does_not_collect(tmp_path: Path) -> None:
    data_dir = _write_mini_parquet(tmp_path)
    lf = ingest_synthetic_data(data_dir)
    # Accessing schema must not raise — confirms lazy frame is valid without I/O
    assert len(lf.collect_schema()) == 23


def test_nonexistent_dir_raises() -> None:
    with pytest.raises(DataIngestionError, match="not found"):
        ingest_synthetic_data(Path("/nonexistent/path"))


# ------------------------------------------------------------------
# load_bad_windows_registry
# ------------------------------------------------------------------

def test_registry_returns_lazyframe(tmp_path: Path) -> None:
    reg_path = tmp_path / "registry.parquet"
    _write_mini_registry(reg_path)
    result = load_bad_windows_registry(reg_path)
    assert isinstance(result, pl.LazyFrame)


def test_registry_has_7_columns(tmp_path: Path) -> None:
    reg_path = tmp_path / "registry.parquet"
    _write_mini_registry(reg_path)
    lf = load_bad_windows_registry(reg_path)
    assert len(lf.collect_schema()) == 7


def test_registry_nonexistent_raises() -> None:
    with pytest.raises(DataIngestionError, match="not found"):
        load_bad_windows_registry(Path("/nonexistent/registry.parquet"))
