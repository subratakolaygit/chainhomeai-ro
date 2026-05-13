"""TagRegistry — PI-System-inspired per-sensor metadata store."""
from __future__ import annotations

from pathlib import Path

import polars as pl
from pydantic import BaseModel, model_validator

from src.ingestion.exceptions import TagRegistryError


class TagSpec(BaseModel):
    """Metadata for one sensor tag, loaded from RO1A_working_Rules_v1.csv."""

    column_name: str
    csv_name: str
    benchmark: float
    idle_value: float | None
    stabilization_mins: float
    allowed_variance_pct: float
    normal_range_min: float
    normal_range_max: float
    failure_indicator: str

    @model_validator(mode="after")
    def _check_benchmark_in_range(self) -> TagSpec:
        if not (self.normal_range_min <= self.benchmark <= self.normal_range_max):
            raise ValueError(
                f"{self.csv_name}: benchmark {self.benchmark} not in "
                f"[{self.normal_range_min}, {self.normal_range_max}]"
            )
        return self


class TagRegistry:
    """Loads and exposes TagSpec metadata for all 12 RO1A sensor tags."""

    def __init__(self, rules_csv_path: Path) -> None:
        """
        Load tag metadata from the rules CSV.

        Args:
            rules_csv_path: Path to RO1A_working_Rules_v1.csv.

        Raises:
            TagRegistryError: CSV not found or contains malformed rows.
        """
        if not rules_csv_path.exists():
            raise TagRegistryError(f"Rules CSV not found: {rules_csv_path}")

        try:
            df = pl.read_csv(rules_csv_path)
        except Exception as exc:
            raise TagRegistryError(f"Failed to read rules CSV: {exc}") from exc

        self._tags: dict[str, TagSpec] = {}
        for row in df.iter_rows(named=True):
            csv_name: str = row["Parameter"]
            column_name = csv_name.lower()  # e.g. RO1A_Feed_Press → ro1a_feed_press

            raw_idle = row["Idle_Value"]
            raw_stab = row["Stabilization_Mins"]

            spec = TagSpec(
                column_name=column_name,
                csv_name=csv_name,
                benchmark=float(row["Benchmark Data"]),
                idle_value=float(raw_idle) if raw_idle is not None else None,
                stabilization_mins=float(raw_stab) if raw_stab is not None else 0.0,
                allowed_variance_pct=float(row["Allowed_Variance_Pct"]),
                normal_range_min=float(row["Normal_Range_Min"]),
                normal_range_max=float(row["Normal_Range_Max"]),
                failure_indicator=row["Failure_Indicator"],
            )
            self._tags[column_name] = spec

    def get_tag(self, column_name: str) -> TagSpec:
        """
        Return the TagSpec for a sensor column.

        Args:
            column_name: Polars column name, e.g. 'ro1a_feed_press'.

        Raises:
            TagRegistryError: Tag not found in registry.
        """
        if column_name not in self._tags:
            raise TagRegistryError(
                f"Unknown tag {column_name!r}. Known: {list(self._tags)}"
            )
        return self._tags[column_name]

    def all_tags(self) -> list[TagSpec]:
        """Return all loaded TagSpec instances."""
        return list(self._tags.values())

    def is_in_normal_range(self, column_name: str, value: float) -> bool:
        """
        Check whether value falls within the tag's normal operating range.

        Args:
            column_name: Sensor column name.
            value: Sensor reading to check.

        Returns:
            True if normal_range_min <= value <= normal_range_max.

        Raises:
            TagRegistryError: Tag not found.
        """
        spec = self.get_tag(column_name)
        return spec.normal_range_min <= value <= spec.normal_range_max
