# CLAUDE.md — ChainHomeAI RO Predictive Maintenance Platform

> **Place at:** `C:\chainhomeai\code\CLAUDE.md`
> Read automatically by Claude Code at session start. Keep updated as architecture evolves.

---

## Project Mission

Early-warning system for a Reverse Osmosis (RO) water-treatment plant.
**Goal:** Predict pump/membrane failure 12–72 hours before it occurs.
**Why:** RO failure = loss of water supply. Early detection enables proactive maintenance.

---

## Repository Layout

```
C:\chainhomeai\
├── code\
│   ├── CLAUDE.md                          ← you are here
│   ├── Prod_prompt.md                     ← master Claude Code prompt (v2.0)
│   ├── RO_SDD.md                          ← System Design Document (append only)
│   ├── DEV_GUIDE.md                       ← step-by-step developer checklist (NEW v2.0)
│   ├── config.py                          ← all typed constants, no magic numbers
│   ├── .github/
│   │   └── workflows/
│   │       └── ci.yml                     ← GitHub Actions CI/CD pipeline (NEW v2.0)
│   ├── .pre-commit-config.yaml            ← pre-commit hooks: Ruff + smoke tests (NEW v2.0)
│   ├── poc\
│   │   ├── scr_14_rul_cip_prediction.py   ← POC RUL model (reference, do not edit)
│   │   └── dashboard.py                   ← POC Streamlit dashboard (extend this)
│   ├── src\
│   │   ├── ingestion\                     ← data loading & schema validation
│   │   ├── features\                      ← feature engineering pipeline
│   │   ├── models\                        ← training, evaluation, MLflow logging
│   │   ├── alerts\                        ← threshold logic & notification engine
│   │   ├── tags\                          ← TagRegistry (PI-System-inspired)
│   │   ├── rag\                           ← HuggingFace + LangChain RAG layer (NEW v2.0)
│   │   └── dashboard\                     ← Streamlit app (production version)
│   ├── tests\
│   │   ├── ingestion\
│   │   ├── features\
│   │   ├── models\
│   │   ├── alerts\
│   │   └── rag\                           ← RAG retrieval quality tests (NEW v2.0)
│   ├── data\
│   │   ├── raw\                           ← original CSVs (read-only, never modify)
│   │   ├── synthetic\                     ← generated 4-year dataset (Parquet)
│   │   └── processed\                     ← cleaned, feature-engineered Parquet files
│   ├── mlruns\                            ← MLflow local experiment store
│   ├── rag_index\                         ← FAISS vector index (NEW v2.0)
│   ├── Dockerfile
│   └── docker-compose.yml
└── docs\
    ├── RO1A_Project_Plain_Language_Summary.md
    └── RO1A_working_Rules_v1.csv          ← ONLY reference benchmark data
```

---

## Architecture Overview

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
[7] Streamlit Dashboard      — Health score, RUL, alert level, action + RAG explanation

All code → GitHub → CI/CD (GitHub Actions) → PR review → merge
```

---

## Naming Conventions

### Files
- `scr_` prefix = standalone scripts (POC legacy)
- `src/` modules use snake_case, no prefix
- Data files: `ro1a_raw_YYYY.parquet`, `ro1a_features_v{N}.parquet`
- Model artefacts: `rul_rf_v{N}.pkl`, `rul_xgb_v{N}.json`
- RAG index: `rag_index/ro1a_rules_index.faiss`
- GitHub branches: `feature/phase-{N}-{short-name}`, `hotfix/name`

### Python

| Element | Convention | Example |
|---|---|---|
| Modules | snake_case | `feature_engineering.py` |
| Classes | PascalCase | `TagRegistry`, `DataIngestionError`, `RagExplainer` |
| Functions | snake_case | `compute_npd_rolling()`, `build_rag_chain()` |
| Constants | UPPER_SNAKE | `ALERT_THRESHOLD_HOURS = 72` |
| Type aliases | PascalCase | `SensorFrame = pl.LazyFrame` |

### Sensor Tags (PI-System style)
Format: `{unit}_{sensor}_{statistic}_{window}`
- `ro1a_pressure_mean_1h`
- `ro1a_flow_delta_6h`
- `ro1a_npd_kurtosis_24h`
- `ro1a_cip_cycle_count`

---

## Key Domain Concepts

| Term | Meaning |
|---|---|
| RO | Reverse Osmosis — the membrane filtration unit being monitored |
| CIP | Clean-In-Place — scheduled chemical wash cycle; resets membrane fouling |
| NPD | Normalised Pressure Differential — primary proxy for membrane health |
| RUL | Remaining Useful Life — hours until predicted failure/mandatory CIP |
| ETP | Effluent Treatment Plant — the wider water-treatment facility |
| RAG | Retrieval-Augmented Generation — retrieve relevant rules then generate explanation |
| FAISS | Local vector store used by LangChain for rule retrieval |
| Bad sensor window | Period of known-invalid readings. Flagged but retained in dataset |

---

## Common Gotchas

### Polars
- **Never use `.to_pandas()`** — find the Polars equivalent
- Use `scan_parquet()` / `scan_csv()` (lazy), not `read_parquet()` (eager), for large files
- `group_by_dynamic()` for time-window aggregations — not `rolling()` (deprecated)
- Schema must be declared explicitly — do not rely on type inference for sensor data
- Use `.with_columns()` chains, not loops, for feature creation

### Time Series
- Always sort by timestamp before any windowed operation
- CIP cycles reset the fouling clock — features computed relative to last CIP, not absolute time
- Test/train split must be **time-based** (no random shuffle) — prevents data leakage

### HuggingFace + LangChain (RAG Layer)
- Store HuggingFace token in GitHub Secrets as `HF_TOKEN` — never hardcode
- Default embedding model: `sentence-transformers/all-MiniLM-L6-v2` (lightweight, runs in Docker)
- FAISS index lives at `rag_index/ro1a_rules_index.faiss` — rebuild if rules CSV changes
- LangChain chain must be stateless — no session memory between alert invocations
- RAG explanations are informational only — **never gate safety-critical alert logic on LLM output**

### GitHub / CI/CD
- Never push directly to `main` or `develop` — always feature branch + PR
- CI must be green before requesting review
- Install pre-commit hooks once: `pre-commit install`
- GitHub Secrets: `HF_TOKEN` and `MLFLOW_TRACKING_URI` — set in repo Settings → Secrets

### Docker on Windows
- Use `pathlib.PurePosixPath` inside containers, `pathlib.PureWindowsPath` on host
- Volume mount syntax: use forward slashes even on Windows host paths
- Set `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUNBUFFERED=1` in Dockerfile

### MLflow
- Set `MLFLOW_TRACKING_URI=file:///app/mlruns` in docker-compose environment
- Always log: model params, RMSE, MAE, feature importances, training data hash

---

## Development Workflow

1. Create feature branch: `git checkout -b feature/phase-{N}-{name}`
2. **Plan first** — describe logic in plain language; get approval before coding
3. **Implement** — write code, update `RO_SDD.md`
4. **Test locally** — `pytest tests/` must pass; add Hypothesis tests for invariants
5. **Lint locally** — `ruff check . && ruff format .` must be clean
6. **Pre-commit** — `pre-commit run --all-files`
7. **Push & open PR** — target `develop` branch
8. **CI green** — GitHub Actions must pass all checks
9. **Review & merge** — at least one reviewer approval required
10. **Document** — update `CLAUDE.md` and `RO_SDD.md` if architecture changes

---

## LLM Integration — Phase 6

HuggingFace Transformers + LangChain for alert explanation text, implemented in `src/rag/`. **Confined to the explanation layer only** — the core prediction pipeline remains deterministic and auditable. No LLM calls in ingestion, feature, model, or alert stages.

RAG corpus: `RO1A_working_Rules_v1.csv` + phase logs + maintenance knowledge base.
Vector store: FAISS. Orchestration: LangChain. Embedding: `sentence-transformers/all-MiniLM-L6-v2`.

---

*Last updated: 2026-03-21 | Version: 2.0*
