"""Central constants for ChainHomeAI — no magic numbers in pipeline modules."""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).parent
SYNTHETIC_DATA_DIR: Path = BASE_DIR / "data" / "synthetic"
BAD_WINDOWS_REGISTRY_PATH: Path = SYNTHETIC_DATA_DIR / "ro1a_bad_windows_registry.parquet"
RULES_CSV_PATH: Path = BASE_DIR.parent / "docs" / "RO1A_working_Rules_v1.csv"

# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------
INGESTION_CHUNK_SIZE: int = 100_000
MAX_RAM_GB: float = 2.0

# ---------------------------------------------------------------------------
# Dataset timeline
# ---------------------------------------------------------------------------
DATASET_START_YEAR: int = 2022
DATASET_END_YEAR: int = 2025
SAMPLE_INTERVAL_MINUTES: int = 1

# ---------------------------------------------------------------------------
# Sensor benchmarks  (source: RO1A_working_Rules_v1.csv)
# ---------------------------------------------------------------------------
FEED_PRESS_BENCHMARK: float = 21.25
INLET_COND_BENCHMARK: float = 15332.683
INLET_FLOW_BENCHMARK: float = 24.6
INLET_ORP_BENCHMARK: float = 1185.0
INLET_PH_BENCHMARK: float = 9.5
PERM_COND_BENCHMARK: float = 133.25
PERM_FLOW_BENCHMARK: float = 16.73
PERM_PH_BENCHMARK: float = 8.97
REJECT_PRESS_BENCHMARK: float = 14.9
REJECT_FLOW_BENCHMARK: float = 7.87
PERM_PRESS_BENCHMARK: float = 0.5
FEED_TEMP_BENCHMARK: float = 25.0

# ---------------------------------------------------------------------------
# Normal ranges  (source: RO1A_working_Rules_v1.csv)
# ---------------------------------------------------------------------------
FEED_PRESS_RANGE: tuple[float, float] = (20.825, 21.675)
INLET_COND_RANGE: tuple[float, float] = (14106.069, 16559.298)
INLET_FLOW_RANGE: tuple[float, float] = (24.108, 25.092)
INLET_ORP_RANGE: tuple[float, float] = (1090.2, 1279.8)
INLET_PH_RANGE: tuple[float, float] = (9.0, 10.0)
PERM_COND_RANGE: tuple[float, float] = (122.59, 143.91)
PERM_FLOW_RANGE: tuple[float, float] = (16.395, 17.065)
PERM_PH_RANGE: tuple[float, float] = (8.47, 9.47)
REJECT_PRESS_RANGE: tuple[float, float] = (13.708, 16.092)
REJECT_FLOW_RANGE: tuple[float, float] = (7.24, 8.5)
PERM_PRESS_RANGE: tuple[float, float] = (0.46, 0.54)
FEED_TEMP_RANGE: tuple[float, float] = (23.75, 26.25)

# ---------------------------------------------------------------------------
# Synthetic data — degradation parameters
# ---------------------------------------------------------------------------
NPD_INITIAL: float = (FEED_PRESS_BENCHMARK - PERM_PRESS_BENCHMARK) / INLET_FLOW_BENCHMARK
NPD_CIP_THRESHOLD: float = 1.05  # NPD level that forces a CIP

# Target days between CIP events, by year (membrane fouls faster as it ages)
CIP_INTERVAL_DAYS: dict[int, float] = {
    2022: 90.0,
    2023: 70.0,
    2024: 50.0,
    2025: 35.0,
}

CIP_DURATION_MINUTES: int = 360  # 6-hour CIP wash

# NPD fouling slope relative to Year 1 baseline
NPD_SLOPE_MULTIPLIER: dict[int, float] = {
    2022: 1.0,
    2023: 1.25,
    2024: 2.0,
    2025: 3.0,
}

# Post-CIP NPD baseline: fractional creep above NPD_INITIAL (permanent membrane damage)
POST_CIP_BASELINE_CREEP: dict[int, float] = {
    2022: 0.00,
    2023: 0.04,
    2024: 0.10,
    2025: 0.175,
}

# Permeate conductivity aging drift — µS/cm per day (salt rejection degradation)
PERM_COND_DRIFT_PER_DAY: dict[int, float] = {
    2022: 0.000,
    2023: 0.010,
    2024: 0.030,
    2025: 0.060,
}

# Gaussian noise sigma at Year 1 level; scaled by NOISE_SCALE_BY_YEAR at runtime
BASE_NOISE_SIGMA: dict[str, float] = {
    "ro1a_feed_press": 0.05,
    "ro1a_inlet_cond": 5.0,
    "ro1a_inlet_flow": 0.02,
    "ro1a_inlet_orp": 2.0,
    "ro1a_inlet_ph": 0.01,
    "ro1a_perm_cond": 0.5,
    "ro1a_perm_flow": 0.02,
    "ro1a_perm_ph": 0.01,
    "ro1a_reject_press": 0.05,
    "ro1a_reject_flow": 0.02,
    "ro1a_perm_press": 0.005,
    "ro1a_feed_temp": 0.1,
    "npd": 0.002,
}

# Noise multiplier by year (mechanical wear increases sensor variability)
NOISE_SCALE_BY_YEAR: dict[int, float] = {
    2022: 1.0,
    2023: 1.2,
    2024: 1.8,
    2025: 2.5,
}

# Feed temperature seasonal amplitude (±°C around benchmark)
FEED_TEMP_AMPLITUDE: float = 3.0

# ---------------------------------------------------------------------------
# Bad-window injection  (counts distributed across all 4 years)
# ---------------------------------------------------------------------------
BAD_WINDOWS_PER_YEAR: dict[int, dict[str, int]] = {
    2022: {"dropout": 2, "stuck_value": 1, "spike": 3, "calibration_drift": 0, "noise_burst": 0},
    2023: {"dropout": 2, "stuck_value": 2, "spike": 3, "calibration_drift": 1, "noise_burst": 1},
    2024: {"dropout": 3, "stuck_value": 2, "spike": 3, "calibration_drift": 1, "noise_burst": 1},
    2025: {"dropout": 2, "stuck_value": 1, "spike": 3, "calibration_drift": 0, "noise_burst": 1},
}

# ---------------------------------------------------------------------------
# Data quality detection
# ---------------------------------------------------------------------------
DATA_QUALITY_STUCK_WINDOW_MINS: int = 30  # rolling window size in rows (1 row = 1 minute)
DATA_QUALITY_SPIKE_SIGMA: float = 3.0  # spike when |value - benchmark| > sigma × half_range
DATA_QUALITY_STUCK_STD_EPSILON: float = 1e-6  # rolling std below this → sensor is stuck

# ---------------------------------------------------------------------------
# Alert thresholds
# ---------------------------------------------------------------------------
ALERT_AMBER_HOURS: float = 72.0
ALERT_RED_HOURS: float = 24.0

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
RANDOM_SEED: int = 42
