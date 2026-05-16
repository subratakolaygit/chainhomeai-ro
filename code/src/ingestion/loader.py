"""Ingestion loader — streams validated sensor Parquet as a Polars LazyFrame."""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

from src.ingestion.exceptions import DataIngestionError
from src.ingestion.schema import SensorFrameSchema

logger = logging.getLogger(__name__)


def ingest_synthetic_data(
    data_dir: Path,
    *,
    strict_schema: bool = True,
) -> pl.LazyFrame:
    """
    Open all year-partitioned Parquet files as a single validated LazyFrame.

    The frame is never collected here — callers decide when and how to
    execute the query plan (streaming, chunked, or full collect).

    Args:
        data_dir: Directory containing year=YYYY/ sub-folders.
        strict_schema: If True, raises on unexpected extra columns.

    Returns:
        Validated LazyFrame covering all available years.

    Raises:
        DataIngestionError: Directory not found, no Parquet files, or schema mismatch.
    """
    if not data_dir.exists():
        raise DataIngestionError(f"Data directory not found: {data_dir}")

    parquet_glob = str(data_dir / "year=*" / "*.parquet")
    try:
        lf = pl.scan_parquet(parquet_glob)
    except Exception as exc:
        raise DataIngestionError(f"Failed to open Parquet files at {data_dir}: {exc}") from exc

    SensorFrameSchema.validate(lf, strict=strict_schema)
    logger.info("Ingestion opened: %s (schema valid)", data_dir)
    return lf


def load_bad_windows_registry(registry_path: Path) -> pl.LazyFrame:
    """
    Open the bad-windows registry Parquet as a LazyFrame.

    Args:
        registry_path: Path to ro1a_bad_windows_registry.parquet.

    Returns:
        LazyFrame with 7 registry columns.

    Raises:
        DataIngestionError: File not found or unreadable.
    """
    if not registry_path.exists():
        raise DataIngestionError(f"Bad-windows registry not found: {registry_path}")

    try:
        lf = pl.scan_parquet(str(registry_path))
    except Exception as exc:
        raise DataIngestionError(
            f"Failed to open bad-windows registry at {registry_path}: {exc}"
        ) from exc

    logger.info("Bad-windows registry opened: %s", registry_path)
    return lf
