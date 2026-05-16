"""Algorithmic data quality detection — runs on any LazyFrame without prior fault knowledge."""

from __future__ import annotations

import polars as pl
from config import (
    DATA_QUALITY_SPIKE_SIGMA,
    DATA_QUALITY_STUCK_STD_EPSILON,
    DATA_QUALITY_STUCK_WINDOW_MINS,
)

from src.tags.tag_registry import TagRegistry

_SENSOR_COLS: list[str] = [
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


def detect_data_quality(
    lf: pl.LazyFrame,
    registry: TagRegistry,
    *,
    stuck_window: int = DATA_QUALITY_STUCK_WINDOW_MINS,
    spike_sigma: float = DATA_QUALITY_SPIKE_SIGMA,
) -> pl.LazyFrame:
    """
    Detect stuck values and spikes algorithmically; update quality columns in-place.

    Only GOOD rows can be promoted to BAD — existing BAD/UNCERTAIN rows are preserved.
    No .collect() is called; the returned LazyFrame stays fully lazy.

    Args:
        lf: Validated LazyFrame (output of ingest_synthetic_data or any matching frame).
        registry: TagRegistry supplying per-sensor benchmark and normal range.
        stuck_window: Rolling window in rows for stuck-value detection (1 row = 1 minute).
        spike_sigma: Flag as spike when |value − benchmark| > sigma × half_range_width.

    Returns:
        LazyFrame with updated data_quality_flag, data_quality_issue_type,
        and data_quality_affected_sensors columns.
    """
    lf = lf.sort("timestamp")

    # Cast Categorical → String so when/then/otherwise can use string literals.
    lf = lf.with_columns(
        pl.col("data_quality_flag").cast(pl.String),
        pl.col("data_quality_issue_type").cast(pl.String),
    )

    # ── Per-sensor intermediate boolean columns ───────────────────────────────
    stuck_exprs: list[pl.Expr] = []
    spike_exprs: list[pl.Expr] = []

    for col in _SENSOR_COLS:
        spec = registry.get_tag(col)
        half_range = (spec.normal_range_max - spec.normal_range_min) / 2.0
        spike_threshold = spike_sigma * half_range

        # Stuck: rolling std near zero over the full window.
        # Null std (window not yet full, or all-null dropout) → treated as not stuck.
        stuck_exprs.append(
            pl.col(col)
            .rolling_std(window_size=stuck_window)
            .fill_null(1.0)
            .le(DATA_QUALITY_STUCK_STD_EPSILON)
            .alias(f"_stuck_{col}")
        )

        # Spike: large deviation from benchmark OR value outside the normal operating range.
        # Null sensor value (dropout fault) → False, not a spike.
        spike_exprs.append(
            (
                (pl.col(col) - spec.benchmark).abs().gt(spike_threshold)
                | pl.col(col).lt(spec.normal_range_min)
                | pl.col(col).gt(spec.normal_range_max)
            )
            .fill_null(False)
            .alias(f"_spike_{col}")
        )

    lf = lf.with_columns(stuck_exprs + spike_exprs)

    # ── Aggregate flags across all sensors ───────────────────────────────────
    stuck_cols = [pl.col(f"_stuck_{c}") for c in _SENSOR_COLS]
    spike_cols = [pl.col(f"_spike_{c}") for c in _SENSOR_COLS]

    lf = lf.with_columns(
        pl.any_horizontal(stuck_cols).alias("_any_stuck"),
        pl.any_horizontal(spike_cols).alias("_any_spike"),
    ).with_columns(
        (pl.col("_any_stuck") | pl.col("_any_spike")).alias("_any_bad"),
    )

    # ── Affected sensors: comma-separated names where a flag fired ────────────
    affected_parts = [
        pl.when(pl.col(f"_stuck_{c}") | pl.col(f"_spike_{c}"))
        .then(pl.lit(c))
        .otherwise(pl.lit(None))
        for c in _SENSOR_COLS
    ]
    new_affected = pl.concat_str(affected_parts, separator=",", ignore_nulls=True)

    # ── Update quality columns — only for rows currently labelled GOOD ────────
    is_good = pl.col("data_quality_flag") == "GOOD"
    newly_bad = is_good & pl.col("_any_bad")

    lf = lf.with_columns(
        # Flag: GOOD → BAD where detected; all other flags unchanged.
        pl.when(newly_bad)
        .then(pl.lit("BAD"))
        .otherwise(pl.col("data_quality_flag"))
        .cast(pl.Categorical)
        .alias("data_quality_flag"),
        # Issue type: stuck_value > spike priority; preserve existing non-GOOD labels.
        pl.when(newly_bad & pl.col("_any_stuck"))
        .then(pl.lit("stuck_value"))
        .when(newly_bad & pl.col("_any_spike"))
        .then(pl.lit("spike"))
        .otherwise(pl.col("data_quality_issue_type"))
        .cast(pl.Categorical)
        .alias("data_quality_issue_type"),
        # Affected sensors: fresh comma-sep list for newly detected rows only.
        pl.when(newly_bad)
        .then(new_affected)
        .otherwise(pl.col("data_quality_affected_sensors"))
        .alias("data_quality_affected_sensors"),
    )

    # ── Drop all intermediate columns ─────────────────────────────────────────
    to_drop = (
        [f"_stuck_{c}" for c in _SENSOR_COLS]
        + [f"_spike_{c}" for c in _SENSOR_COLS]
        + ["_any_stuck", "_any_spike", "_any_bad"]
    )
    return lf.drop(to_drop)
