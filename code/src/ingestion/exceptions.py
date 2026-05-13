"""Custom exception classes for the ingestion pipeline."""
from __future__ import annotations


class DataIngestionError(ValueError):
    """Raised when sensor data fails schema validation or cannot be read."""


class TagRegistryError(KeyError):
    """Raised when TagRegistry cannot locate a tag or load the rules CSV."""
