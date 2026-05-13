"""Tests for TagSpec and TagRegistry."""
from __future__ import annotations

import pytest
from config import RULES_CSV_PATH
from pydantic import ValidationError
from src.ingestion.exceptions import TagRegistryError
from src.tags.tag_registry import TagRegistry, TagSpec


@pytest.fixture(scope="module")
def registry() -> TagRegistry:
    return TagRegistry(RULES_CSV_PATH)


def test_loads_12_tags(registry: TagRegistry) -> None:
    assert len(registry.all_tags()) == 12


def test_get_feed_press(registry: TagRegistry) -> None:
    spec = registry.get_tag("ro1a_feed_press")
    assert spec.benchmark == pytest.approx(21.25)
    assert spec.normal_range_min == pytest.approx(20.825)
    assert spec.normal_range_max == pytest.approx(21.675)


def test_get_unknown_tag_raises(registry: TagRegistry) -> None:
    with pytest.raises(TagRegistryError):
        registry.get_tag("ro1a_nonexistent")


def test_in_normal_range_true(registry: TagRegistry) -> None:
    assert registry.is_in_normal_range("ro1a_feed_press", 21.0) is True


def test_in_normal_range_false_below(registry: TagRegistry) -> None:
    assert registry.is_in_normal_range("ro1a_feed_press", 5.0) is False


def test_in_normal_range_false_above(registry: TagRegistry) -> None:
    assert registry.is_in_normal_range("ro1a_feed_press", 99.0) is False


def test_all_tags_have_valid_benchmarks(registry: TagRegistry) -> None:
    for spec in registry.all_tags():
        assert spec.normal_range_min <= spec.benchmark <= spec.normal_range_max


def test_tagspec_invalid_range_raises() -> None:
    with pytest.raises(ValidationError):
        TagSpec(
            column_name="ro1a_test",
            csv_name="RO1A_Test",
            benchmark=100.0,
            idle_value=None,
            stabilization_mins=0.0,
            allowed_variance_pct=5.0,
            normal_range_min=200.0,   # min > benchmark — invalid
            normal_range_max=300.0,
            failure_indicator="Test",
        )


def test_missing_csv_raises(tmp_path: pytest.TempPathFactory) -> None:
    with pytest.raises(TagRegistryError):
        TagRegistry(tmp_path / "nonexistent.csv")
