"""Expected Polars schema for the RO1A synthetic dataset and its validator."""
from __future__ import annotations

import polars as pl

from src.ingestion.exceptions import DataIngestionError

# Authoritative 23-column schema — single source of truth for the pipeline.
EXPECTED_SCHEMA: dict[str, pl.DataType] = {
    "timestamp": pl.Datetime("us", "UTC"),
    "ro1a_feed_press": pl.Float32,
    "ro1a_inlet_cond": pl.Float32,
    "ro1a_inlet_flow": pl.Float32,
    "ro1a_inlet_orp": pl.Float32,
    "ro1a_inlet_ph": pl.Float32,
    "ro1a_perm_cond": pl.Float32,
    "ro1a_perm_flow": pl.Float32,
    "ro1a_perm_ph": pl.Float32,
    "ro1a_reject_press": pl.Float32,
    "ro1a_reject_flow": pl.Float32,
    "ro1a_perm_press": pl.Float32,
    "ro1a_feed_temp": pl.Float32,
    "npd": pl.Float32,
    "cip_cycle_number": pl.UInt8,
    "hours_since_last_cip": pl.Float32,
    "rul_hours": pl.Float32,
    "failure_imminent": pl.Boolean,
    "days_since_start": pl.Float32,
    "data_quality_flag": pl.Categorical,
    "data_quality_issue_type": pl.Categorical,
    "data_quality_affected_sensors": pl.String,
    "data_quality_window_id": pl.UInt16,
}


class SensorFrameSchema:
    """Validates a Polars LazyFrame schema without triggering any data I/O."""

    @classmethod
    def validate(cls, lf: pl.LazyFrame, *, strict: bool = True) -> None:
        """
        Check that lf matches EXPECTED_SCHEMA.

        Args:
            lf: LazyFrame to validate (schema checked; no data scanned).
            strict: If True, raises on unexpected extra columns.

        Raises:
            DataIngestionError: Missing columns, dtype mismatches, or (strict) extra columns.
        """
        actual = lf.collect_schema()

        missing = [col for col in EXPECTED_SCHEMA if col not in actual]
        if missing:
            raise DataIngestionError(f"Missing columns: {missing}")

        mismatches = [
            f"{col}: expected {EXPECTED_SCHEMA[col]}, got {actual[col]}"
            for col in EXPECTED_SCHEMA
            if col in actual and actual[col] != EXPECTED_SCHEMA[col]
        ]
        if mismatches:
            raise DataIngestionError(f"Dtype mismatches: {mismatches}")

        if strict:
            extra = [col for col in actual if col not in EXPECTED_SCHEMA]
            if extra:
                raise DataIngestionError(f"Unexpected columns (strict=True): {extra}")
