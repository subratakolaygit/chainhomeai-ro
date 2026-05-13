"""
Entrypoint: generate the 4-year RO1A synthetic dataset and inject bad windows.

Run from C:\\chainhomeai\\code\\:
    python scripts/generate_synthetic.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure repo root (code/) is on sys.path when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    BAD_WINDOWS_REGISTRY_PATH,
    DATASET_END_YEAR,
    DATASET_START_YEAR,
    SYNTHETIC_DATA_DIR,
)
from src.ingestion.bad_window_injector import BadWindowInjector, write_bad_windows_registry
from src.ingestion.synthetic_generator import SyntheticRO1AGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info(
        "Generating synthetic dataset  years %d–%d → %s",
        DATASET_START_YEAR, DATASET_END_YEAR, SYNTHETIC_DATA_DIR,
    )

    generator = SyntheticRO1AGenerator(output_dir=SYNTHETIC_DATA_DIR)
    injector = BadWindowInjector(starting_window_id=1)
    all_registry_rows: list[dict] = []

    for year in range(DATASET_START_YEAR, DATASET_END_YEAR + 1):
        logger.info("── Year %d ──", year)
        df = generator._generate_year(year)  # noqa: SLF001
        df, registry_rows = injector.inject(df, year)

        year_dir = SYNTHETIC_DATA_DIR / f"year={year}"
        year_dir.mkdir(parents=True, exist_ok=True)
        out_path = year_dir / "ro1a_synthetic.parquet"
        df.write_parquet(out_path)
        logger.info("  %d rows written → %s", len(df), out_path)

        all_registry_rows.extend(registry_rows)

    write_bad_windows_registry(all_registry_rows, BAD_WINDOWS_REGISTRY_PATH)
    logger.info("Done. Total bad windows injected: %d", len(all_registry_rows))


if __name__ == "__main__":
    main()
