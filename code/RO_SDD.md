# RO_SDD — System Design Document
## ChainHomeAI RO Predictive Maintenance Platform — v2.0

> **Location:** `C:\chainhomeai\code\RO_SDD.md`
> **Rule:** Append-only. Never delete or overwrite existing entries.
> Each implemented phase must add a new dated section at the bottom.

---

## Document Purpose

Technical audit trail for every engineering decision, component introduced, and phase achieved. Serves as:
- Onboarding reference for new team members
- Evidence of systematic pipeline design for clients and stakeholders

---

## 1. Project Overview

| Field | Value |
|---|---|
| System Name | ChainHomeAI RO Predictive Maintenance Platform |
| Plant | Water Treatment ETP (Effluent Treatment Plant) |
| Asset | RO Unit — RO1A |
| Mission | Detect membrane/pump failure 12–72 hours before occurrence |
| Version | 2.0 — CI/CD + GitHub + RAG + HuggingFace + LangChain |

---

## 2. Technology Stack

### 2a. Core Language & Data Processing

| Component | Choice | Version | Rationale |
|---|---|---|---|
| Runtime | Python | 3.12 | Latest stable; pattern matching, `tomllib`, improved `typing`, faster interpreter |
| Dataframe | Polars | Latest | Rust-backed, zero-copy, native lazy evaluation. 2–10× faster than Pandas on 10 GB+ sensor datasets |
| In-process SQL | DuckDB | Latest | Columnar analytics on Parquet. Zero-copy Polars LazyFrame integration |
| Storage | Apache Parquet | — | Columnar compression; ~40 GB CSV → 4–8 GB. Native predicate pushdown |
| Validation | Pydantic v2 | v2.x | Rust-backed. Enforces sensor tag schema at pipeline entry |

### 2b. Feature Engineering & ML

| Component | Choice | Rationale |
|---|---|---|
| Time-series features | tsfresh | 700+ statistically relevant features. Unsupervised discovery of RO fouling indicators |
| Anomaly detection | STUMPY | Matrix Profile — GPU-accelerated. Detects fault patterns not captured by rule-based thresholds |
| Baseline ML | Scikit-learn | Random Forest Regressor for RUL. Feature Importance explainable to non-technical clients |
| Gradient boosting | XGBoost | Superior on tabular sensor data with missing values. Handles irregular time-series gaps |
| Online ML | River | Handles concept drift as membrane ages. Incremental updates — no full retraining |
| Hyperparameter tuning | Optuna | Async TPE sampler. 5–10× faster than GridSearchCV. Pruning support |
| Experiment tracking | MLflow | Local server. Logs params, RMSE, MAE, feature importances, data hash, artefacts |

### 2c. RAG / LLM Layer *(NEW — v2.0)*

| Component | Choice | Rationale |
|---|---|---|
| Embedding model | HuggingFace sentence-transformers | Local model hosting — no cloud API. `all-MiniLM-L6-v2` for sensor log embedding |
| LLM inference | HuggingFace Transformers | Run small LLM locally inside Docker. No cloud dependency |
| RAG orchestration | LangChain | Chain: embed alert context → FAISS retrieve rules → generate plain-language explanation |
| Vector store | FAISS (via LangChain) | Local vector index over `RO1A_working_Rules_v1.csv` + maintenance knowledge base |
| Document loaders | LangChain loaders | Ingest CSV rules, Markdown docs, phase logs into RAG corpus |

### 2d. CI/CD & GitHub Integration *(NEW — v2.0)*

| Component | Choice | Rationale |
|---|---|---|
| CI/CD pipeline | GitHub Actions | Every PR: Ruff lint, pytest + coverage, Docker build verification |
| Branch protection | GitHub branch rules | `main` requires passing CI + PR review. Enforced at repository level |
| Pre-commit hooks | pre-commit framework | Ruff lint + format + smoke tests before every commit |
| Secrets management | GitHub Secrets | `HF_TOKEN`, `MLFLOW_TRACKING_URI` stored as encrypted secrets |
| Dependency updates | Dependabot | Automated PRs for security patches in `requirements.txt` |

### 2e. Code Quality

| Component | Choice | Rationale |
|---|---|---|
| Linting + formatting | Ruff | Single tool replaces flake8, isort, black. 10–100× faster |
| Testing | Pytest + Hypothesis | Property-based testing — random sensor distributions verify pipeline invariants |
| Coverage | pytest-cov | Minimum 80% coverage enforced in CI |
| Dashboard | Streamlit 1.3x | Existing POC extended. `st.cache_data` with Polars-native caching |
| Containerisation | Docker + Docker Compose v2 | Reproducible environment on Windows host. Single-command startup |

---

## 3. Architectural Decisions

### Decision 1: Retain Bad Sensor Data in Raw Dataset
Keep bad-sensor windows (dropouts, stuck values, spikes) in the 4-year dataset. Data cleaning is an **explicit, logged pipeline stage**. A `data_quality_log` column tags bad windows; original records are never deleted.

*Inspired by AVEVA PI System's bad-quality tag approach — value and quality flag travel together.*

### Decision 2: TagRegistry Pattern (PI System-Inspired)
`TagRegistry` class stores metadata per sensor tag: engineering units, valid range, bad-data deadband, compression threshold. Enables automated validation of every incoming value.

### Decision 3: Local Docker, Not Cloud
Air-gapped / cost-sensitive client environment. Docker provides reproducibility without cloud dependency. Sensitive plant data never leaves the site.

### Decision 4: Time-Based Train/Test Split
Training = years 1–3. Test = year 4. No random shuffling — prevents data leakage and replicates real deployment conditions.

### Decision 5: GitHub-First Development *(NEW — v2.0)*
All code through GitHub. No direct commits to `main` or `develop`. Every change requires a PR, passing CI (Ruff + pytest + Docker build), and at least one review. Branch protection enforced at repository level.

### Decision 6: RAG for Alert Explanations Only *(NEW — v2.0)*
LLM/RAG calls are confined to the alert explanation layer. The core prediction pipeline (ingestion → features → model → alert threshold) remains fully deterministic and auditable. Safety-critical failure prediction is never dependent on LLM availability or behaviour.

---

## 4. Architecture Pipeline

| Stage | Component | Technology | Output |
|---|---|---|---|
| 1 | Ingestion Layer | Polars LazyFrame + Pydantic v2 | Validated LazyFrame with `data_quality_log` |
| 2 | Data Quality Stage | Pydantic v2 + TagRegistry | Flagged bad rows (kept, not deleted) |
| 3 | Feature Engineering | tsfresh + Polars + STUMPY | `ro1a_features_vN.parquet` |
| 4 | Model Layer | Scikit-learn + XGBoost + River + Optuna | RUL prediction + MLflow experiment log |
| 5 | Alert Engine | Rules from `RO1A_working_Rules_v1.csv` | 72h amber / 24h red / CIP recommendation |
| 6 | RAG Layer | HuggingFace + LangChain + FAISS | Plain-language alert explanation text |
| 7 | Dashboard | Streamlit 1.3x | Health score, RUL, alert level, explanation |

```
Raw Sensor Data (CSV / Parquet)
        │
        ▼
[1] Ingestion Layer          — Polars LazyFrame streaming, Pydantic v2 schema validation
        │
        ▼
[2] Data Quality Stage       — Bad-data flagging (keep bad rows; log in data_quality_log)
        │
        ▼
[3] Feature Engineering      — Rolling stats, delta tags, cross-sensor correlations,
                               CIP cycle detection, NPD (Normalised Pressure Differential)
        │
        ▼
[4] Model Layer              — Random Forest → XGBoost → STUMPY Matrix Profile
                               All experiments logged to MLflow
        │
        ▼
[5] Alert Engine             — Rule-based thresholds from RO1A_working_Rules_v1.csv
                               72h amber / 24h red / CIP recommendation
        │
        ▼
[6] RAG / LLM Layer          — HuggingFace sentence-transformers + LangChain + FAISS
                               Retrieves relevant rules → generates plain-language explanation
        │
        ▼
[7] Streamlit Dashboard      — Health score, RUL, alert level, action text + RAG explanation

All code → GitHub → CI/CD (GitHub Actions) → PR review → merge
```

---

## 5. Design Inspirations

### Veolia Hubgrade Platform
- Traffic-light health indicators (green / amber / red) on the dashboard
- Recommended corrective action text alongside alerts — not just a colour change
- Multi-asset comparison view architecture (design allows expansion)
- KPI dashboard panels for plant operators

### AVEVA PI System
- Tag-based data model with metadata (engineering units, quality flags, compression deadband)
- `TagRegistry` class stores and validates all tag metadata
- Totaliser tags — cumulative flow totals that reset at CIP boundaries
- Exception-based storage — only store values that change beyond a deadband threshold
- Historical data replay — re-run prediction over historical data to validate against known failures

---

## 6. Phase Log

*Each implemented phase must append a new section below in this format:*

```markdown
## [YYYY-MM-DD] — Phase [N]: [Short Title]

### Components Introduced
- **[Library/Tool]**: [Description]. Reason chosen: [why].

### What This Phase Achieves
[2–3 sentences on the functional outcome.]

### Known Limitations / Next Steps
[Honest assessment.]
```

---

## 7. Glossary

| Term | Definition |
|---|---|
| RO | Reverse Osmosis — membrane filtration unit |
| CIP | Clean-In-Place — scheduled chemical wash; resets membrane fouling clock |
| NPD | Normalised Pressure Differential — primary membrane health KPI |
| RUL | Remaining Useful Life — predicted hours until failure or mandatory CIP |
| ETP | Effluent Treatment Plant — the wider water-treatment facility |
| Tag | Named sensor measurement point with associated metadata (PI System terminology) |
| TagRegistry | Class that stores and validates all tag metadata |
| Deadband | Threshold below which sensor value changes are not stored |
| Matrix Profile | Time-series algorithm for unsupervised anomaly detection (STUMPY) |
| LazyFrame | Polars deferred computation object — query plan not executed until `.collect()` |
| RAG | Retrieval-Augmented Generation — LangChain retrieves relevant rules then generates explanation |
| FAISS | Local vector store used by LangChain for rule retrieval |
| HuggingFace | ML model hub and Transformers library for local embedding and LLM inference |
| LangChain | Framework orchestrating the RAG chain: embed → retrieve → generate |
| CI/CD | Continuous Integration/Deployment — automated test + build on every PR via GitHub Actions |

---

*Created: 2026-03-19 | Version: 2.0 | Updated: 2026-03-22 | Status: Active*

---

## [2026-03-22] — Phase 0: Repository & CI/CD Setup

### Overview
This phase establishes the entire engineering foundation before any ML code is written. The philosophy: **infrastructure first**. Every subsequent phase builds on a stable, automated, version-controlled base. This is standard practice in professional MLOps and production data science teams.

---

### Phase 0.1 — GitHub Repository Creation

**What was done:**
- Created private GitHub repository: `chainhomeai-ro` under account `subratakolaygit`
- Made public after setup (unlimited free GitHub Actions minutes; no sensitive data or credentials in repo)
- Cloned locally to `C:\chainhomeai\code\chainhomeai-ro\`
- Created the full folder structure inside the repo as per `CLAUDE.md` Repository Layout

**Repository structure created:**
```
chainhomeai-ro\                        ← repo root (GitHub)
├── .github\workflows\                 ← GitHub Actions CI/CD pipeline
├── .gitignore                         ← excludes venv, Parquet data, MLflow artefacts, FAISS index
├── .pre-commit-config.yaml            ← pre-commit hooks at repo root (required by git hook)
├── README.md
├── code\                              ← all source code lives here
│   ├── CLAUDE.md                      ← Claude Code context file (updated with GitHub URL)
│   ├── Prod_prompt.md                 ← master Claude Code prompt
│   ├── RO_SDD.md                      ← this document
│   ├── DEV_GUIDE.md                   ← step-by-step developer checklist
│   ├── config.py                      ← all typed constants (no magic numbers in modules)
│   ├── requirements.txt               ← all Python dependencies
│   ├── Dockerfile                     ← stub (full config in Phase 5)
│   ├── pyproject.toml                 ← project metadata + Ruff linter configuration
│   ├── .pre-commit-config.yaml        ← copy kept in code/ for reference
│   ├── src\                           ← production Python packages (ingestion, features, models, alerts, tags, rag, dashboard)
│   ├── tests\                         ← mirrors src/ structure
│   ├── data\raw, synthetic, processed ← raw CSVs and generated Parquet files (gitignored)
│   ├── poc\                           ← reference POC scripts (do not edit)
│   ├── mlruns\                        ← MLflow experiment store (gitignored)
│   └── rag_index\                     ← FAISS vector index (gitignored)
└── docs\                              ← reference documents and benchmark data
```

**Key design decision — `code/` as subdirectory:**
All source code lives inside `code/` rather than at the repo root. This allows `docs/` to sit alongside `code/` at the repo root level, cleanly separating reference documentation from implementation. `.github/` remains at the repo root as GitHub Actions requires it there.

**Components Introduced:**
- **Git + GitHub**: Version control and remote repository hosting. Every change is tracked, reversible, and auditable — critical for a safety system.
- **`.gitignore`**: Prevents large Parquet files (400MB+), MLflow artefacts, FAISS index, and virtual environments from being committed to GitHub.
- **`config.py`**: Central constants file. All thresholds, paths, model parameters, and window sizes defined here as typed Python constants. No magic numbers anywhere in the pipeline modules.
- **`__init__.py` stubs**: All `src/` and `tests/` subdirectories are proper Python packages from day one.

---

### Phase 0.2 — Branch Protection

**What was done:**
- Configured GitHub Ruleset named `protect-main` targeting the `main` branch
- Enabled via GitHub → Settings → Branches → Rulesets (new GitHub UI — replaces older "Branch Protection Rules")

**Rules enforced:**
| Rule | Effect |
|------|--------|
| Require pull request before merging | No direct commits to `main` — ever |
| Require 1 approving review | At least one reviewer must approve before merge |
| Require status checks to pass | CI must be green before merge is allowed |
| Require branches to be up to date | Feature branch must be current with `main` before merge |
| Block force pushes | Prevents history rewriting on `main` |

**Why this matters (interview talking point):**
Branch protection is what separates a hobby project from a production-grade codebase. On a safety-critical system like an RO plant monitor, bad code reaching `main` could mean missed failure alerts or false alarms. The protection rules make it structurally impossible to bypass quality checks — even as the repo owner. This is enforced at the GitHub platform level, not just by convention.

**Lesson learned:**
After enabling branch protection, the next `git push` directly to `main` was rejected with error `GH013: Repository rule violations found`. This confirmed branch protection was working correctly. All subsequent changes moved through the feature branch → PR → CI → merge workflow.

---

### Phase 0.3 — GitHub Actions CI/CD Pipeline

**What was done:**
- Created `.github/workflows/ci.yml` — triggers on every push and PR to `main` and `develop`

**4 CI jobs:**

| Job | Command | Purpose |
|-----|---------|---------|
| `ruff-lint` | `ruff check code/` | Scans for code errors, bad imports, naming violations |
| `ruff-format` | `ruff format --check code/` | Fails if code is not consistently formatted |
| `pytest-coverage` | `pytest tests/ --cov=src --cov-fail-under=80` | Runs all tests; fails if coverage < 80% |
| `docker-build` | `docker build .` | Proves the container image compiles cleanly |

**Components Introduced:**
- **GitHub Actions**: Cloud CI/CD runner. Every PR automatically triggers the 4-job pipeline at no cost (public repo = unlimited minutes).
- **Ruff**: Single tool replacing flake8 (linting), black (formatting), and isort (import sorting). Written in Rust — 10–100× faster than the Python equivalents.
- **pytest-cov**: Coverage measurement. The 80% floor prevents untested code from reaching `main`.

**Why CI/CD matters (interview talking point):**
CI is the automated quality gate. Without it, developers must remember to run checks manually before every merge — and they forget. CI makes quality enforcement structural: the merge button is literally greyed out until all checks pass. For a predictive maintenance system, this matters because a bug in the alert threshold logic could cause false negatives (missed failures) or false positives (unnecessary shutdowns). CI catches regressions before they reach production.

**First CI run results:**
- `ruff-lint` ✅ passed
- `ruff-format` ✅ passed
- `pytest-coverage` ✅ passed
- `docker-build` ❌ failed — no Dockerfile existed yet (expected)

---

### Phase 0.3b — Stub Dockerfile & requirements.txt

**What was done:**
- Created `code/Dockerfile` — minimal Python 3.12-slim image that passes the CI `docker-build` job
- Created `code/requirements.txt` — full dependency list for the project
- This change could not be pushed directly to `main` (branch protection active)
- Created feature branch `feature/phase-0-dockerfile` → pushed → opened PR on GitHub
- CI ran on the PR — all 4 jobs green → merged to `main`

**This was the first PR merged through the full workflow:**
`feature branch → CI green → PR review → merge to main`

**Components Introduced:**
- **Docker**: Packages Python 3.12, all libraries, and application code into a self-contained container. Eliminates "works on my machine" problems. The RO pipeline, MLflow server, and Streamlit dashboard all run inside Docker — identical behaviour on any host.
- **`requirements.txt`**: Pinned dependency list. Every library the pipeline needs is declared explicitly. CI installs from this file, ensuring the test environment matches the Docker environment.

**Known Limitations / Next Steps:**
- Dockerfile is a stub — `CMD ["python", "--version"]` only. Full multi-service configuration (app + MLflow + Streamlit) completed in Phase 5.
- `requirements.txt` uses unpinned versions — will be pinned with exact versions (`pip freeze`) before Phase 5.

---

### Phase 0 — Pre-commit Hook Correction

**Issue encountered:**
The `.pre-commit-config.yaml` smoke test hook pointed to `tests/` (repo root), but tests live at `code/tests/`. The hook failed with `ERROR: file or directory not found: tests/`.

**Fix applied:**
Updated `entry:` in the smoke-tests hook from `pytest tests/` to `pytest code/tests/`. Both copies of the file (`code/.pre-commit-config.yaml` and root `.pre-commit-config.yaml`) updated to stay in sync.

**Why this is documented:**
Path mismatches between local structure and tool configuration are a common source of CI failures on projects with non-standard repo layouts (i.e., source in a subdirectory rather than at the root). The fix demonstrates the importance of running `pre-commit run --all-files` locally before assuming CI will pass.

---

### What Phase 0 Achieves

Phase 0 delivers a production-grade engineering foundation with zero ML code written yet. The repo enforces:
1. **No untested code reaches `main`** — pytest + coverage gate
2. **No unformatted code reaches `main`** — Ruff format gate
3. **No broken containers reach `main`** — Docker build gate
4. **No unreviewed code reaches `main`** — PR + branch protection gate

Every subsequent phase (data, features, models, alerts, RAG) adds functionality on top of this foundation, with CI automatically verifying each addition.

### Known Limitations / Next Steps
- Phase 0.4: Pre-commit hooks to be installed locally (`pre-commit install`)
- Phase 0.5: GitHub Secrets (`HF_TOKEN`, `MLFLOW_TRACKING_URI`) to be added
- Phase 0.6: Python virtual environment setup with pinned dependencies
- Phase 0.7: Full `docker-compose.yml` with app + MLflow + Streamlit services

---

## [2026-05-13] — Phase 1C: Synthetic Dataset + Ingestion Pipeline

### Components Introduced

- **SyntheticRO1AGenerator** (`src/ingestion/synthetic_generator.py`): Generates 2,103,840 rows across 4 year-partitioned Parquet files using NumPy vectorised operations. Models realistic RO membrane degradation: NPD sawtooth fouling curves (slope ×1/1.25/2/3 per year), seasonal feed temperature (sine wave ±3°C), correlated sensor cross-effects (feed pressure rises / permeate flow drops as NPD degrades), Brownian-walk feed quality sensors, and CIP events that reset the fouling clock. Reason: provides a reproducible, physics-grounded training corpus with known ground-truth RUL labels.

- **BadWindowInjector** (`src/ingestion/bad_window_injector.py`): Injects 32 bad-sensor windows (5 types: dropout, stuck-value, spike, calibration-drift, noise-burst) across all 4 years and writes a companion registry Parquet. Reason: the pipeline must handle realistic industrial data quality degradation; injecting known bad windows enables Stage 2 (Data Quality) to be validated against ground truth.

- **SensorFrameSchema + EXPECTED_SCHEMA** (`src/ingestion/schema.py`): Zero-cost 23-column schema validator using `lf.collect_schema()` — checks column presence and dtypes without scanning any data. Reason: catches schema drift at pipeline entry before any computation is triggered.

- **TagRegistry + TagSpec** (`src/tags/tag_registry.py`): Pydantic v2 model per sensor tag loaded from `RO1A_working_Rules_v1.csv`. Stores benchmark, normal range, idle value, stabilization time, and failure indicator. Reason: PI-System-inspired tag metadata store — single source of truth for all threshold decisions in Stage 2 (flagging) and Stage 5 (alerts).

- **Ingestion loader** (`src/ingestion/loader.py`): `ingest_synthetic_data()` streams all year-partitioned Parquet as one validated LazyFrame via `scan_parquet("year=*/*.parquet")`. Never calls `.collect()`. Reason: enforces the memory ≤ 2 GB constraint — the entire 4-year dataset is queried lazily and only materialised in downstream stages.

- **config.py**: All typed constants — paths, benchmarks, normal ranges, degradation parameters, noise scales, CIP schedules, alert thresholds. Reason: eliminates magic numbers from all pipeline modules.

### What This Phase Achieves

The data foundation is complete. A reproducible 4-year synthetic sensor dataset exists on disk, partitioned by year, with 23 columns including ground-truth `rul_hours`, `failure_imminent`, `cip_cycle_number`, and full data-quality provenance. The ingestion pipeline can stream any or all of this data as a validated Polars LazyFrame in under 1 second, ready for feature engineering in Phase 2.

### Known Limitations / Next Steps

- No stabilisation ramp after CIP completion (sensors jump back to operating values instantly rather than ramping over `stabilization_mins`). Acceptable for Phase 1; will be corrected in Phase 2 feature engineering.
- Bad window `affected_sensors` during CIP is set to all 12 sensors for simplicity; Phase 2 Stage 2 (Data Quality) will refine per-sensor flagging.
- Phase 2A next: plan PI-System-inspired feature engineering (rolling statistics, delta tags, NPD trend slope, CIP cycle detection).
