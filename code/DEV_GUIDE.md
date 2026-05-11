# DEV_GUIDE — ChainHomeAI RO Predictive Maintenance Platform
## Step-by-Step Developer Checklist — v1.0

> **Path:** `C:\chainhomeai\code\DEV_GUIDE.md`
> **Follow this document for the entire project. Every step is numbered. Tick as you go.**

---

## HOW TO USE THIS GUIDE

- Follow phases **in order**
- Every phase has numbered steps — do them in sequence
- When you see **🔔 NOTIFY FOR TESTING** — stop, run all tests, fix failures before continuing
- **All code goes through GitHub** — no direct commits to `main` or `develop`
- Every change = `feature branch` → `PR` → `CI green` → `review` → `merge`

---

## PHASE 0 — REPOSITORY & CI/CD SETUP
> *Do this once before any code is written. Everything else builds on this.*

### 0.1 — Create GitHub Repository
1. GitHub → New Repository → name: `chainhomeai-ro` → Private → Add README
2. Clone locally: `git clone https://github.com/yourorg/chainhomeai-ro.git`
3. Create folder structure as per `CLAUDE.md` Repository Layout
4. Add `Prod_prompt.md`, `CLAUDE.md`, `RO_SDD.md`, `DEV_GUIDE.md` to `code/`
5. `git add . && git commit -m "chore: initial repo structure" && git push`

### 0.2 — Branch Protection
1. GitHub → Settings → Branches → Add rule for `main`
2. Enable: **Require status checks to pass before merging**
3. Enable: **Require pull request reviews before merging** (1 reviewer minimum)
4. Enable: **Require branches to be up to date before merging**
5. Save. Nothing merges to `main` without passing CI from this point forward.

### 0.3 — GitHub Actions CI/CD Pipeline
1. Create `.github/workflows/ci.yml`
2. Add job: **ruff-lint** → `pip install ruff && ruff check .`
3. Add job: **ruff-format** → `ruff format --check .`
4. Add job: **pytest-coverage** → `pip install pytest pytest-cov hypothesis && pytest tests/ --cov=src --cov-fail-under=80`
5. Add job: **docker-build** → `docker build .`
6. `git add .github/ && git commit -m "ci: add GitHub Actions CI pipeline" && git push`
7. Verify workflow appears in GitHub Actions tab

### 0.4 — Pre-commit Hooks
1. `pip install pre-commit`
2. Create `.pre-commit-config.yaml` with Ruff hooks (lint + format)
3. `pre-commit install`
4. Test: `pre-commit run --all-files` (should pass on empty repo)

### 0.5 — GitHub Secrets
1. GitHub → Settings → Secrets and Variables → Actions → New secret
2. Add: `HF_TOKEN` (your HuggingFace API token — needed for Phase 6)
3. Add: `MLFLOW_TRACKING_URI` = `file:///app/mlruns`

### 0.6 — Python Environment
1. Install Python 3.12
2. `python -m venv .venv && .venv\Scripts\activate`
3. Create `requirements.txt`: `polars, duckdb, pydantic, tsfresh, stumpy, scikit-learn, xgboost, river, optuna, mlflow, ruff, pytest, hypothesis, pytest-cov, streamlit, pre-commit`
4. `pip install -r requirements.txt`
5. `git add requirements.txt && git commit -m "chore: add requirements.txt" && git push`

### 0.7 — Docker Base Setup
1. Create `Dockerfile`: `FROM python:3.12-slim`
2. Add: `COPY requirements.txt . && RUN pip install -r requirements.txt`
3. Add: `ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1`
4. Create `docker-compose.yml` with app service + MLflow service
5. Set `MLFLOW_TRACKING_URI=file:///app/mlruns` in docker-compose environment
6. Test: `docker-compose up --build` (should start without errors)
7. `git add Dockerfile docker-compose.yml && git commit -m "chore: Docker setup" && git push`

> ✅ **Phase 0 complete** — Repo, CI/CD, branch protection, pre-commit, Docker all confirmed working.

---

## PHASE 1 — DATA FOUNDATION
> *Goal: Generate a realistic 4-year RO sensor dataset and build a validated ingestion pipeline.*

### 1.1 — Plan: Synthetic Data Generation *(Plan Step 1A — no code yet)*
1. Create branch: `git checkout -b feature/phase-1-data-foundation`
2. Write plan (plain language) covering:
   - 4-year timeline with realistic RO degradation curves (NPD rising over ~90-day fouling cycles)
   - Bad-sensor window injection: random dropouts, stuck values, spikes (~5% of data)
   - `data_quality_log` column tagging each bad window with reason code
   - Output Parquet schema + full column dictionary
3. Present plan — **get approval before writing any implementation code**

### 1.2 — Plan: Ingestion Pipeline *(Plan Step 1B — no code yet)*
1. Write pseudocode flowchart covering:
   - Polars `scan_parquet` / `scan_csv` (lazy streaming)
   - Pydantic v2 schema validation at pipeline entry
   - Bad-data detection rules from `RO1A_working_Rules_v1.csv`
   - `TagRegistry` class with engineering units, valid range, deadband per sensor tag
2. Present plan — **get approval before implementing**

### 1.3 — Implement
1. `src/ingestion/synthetic_data.py` — generate 4-year Parquet dataset
2. `src/tags/tag_registry.py` — `TagRegistry` class with metadata per sensor tag
3. `src/ingestion/ingest.py` — streaming ingestion with Pydantic v2 validation
4. `src/ingestion/data_quality.py` — bad-data flagging logic
5. Save outputs to `data/synthetic/` and `data/raw/`
6. Update `config.py` with all constants (no magic numbers in modules)
7. Append Phase 1 entry to `RO_SDD.md`

### 1.4 — 🔔 NOTIFY FOR TESTING
1. `tests/ingestion/test_synthetic_data.py` — verify schema, row count, date range
2. `tests/ingestion/test_ingest.py` — Hypothesis tests verifying schema invariants
3. `tests/ingestion/test_data_quality.py` — verify bad-data flagging on known-bad windows
4. Run: `pytest tests/ingestion/ -v` — all must pass
5. Run: `ruff check . && ruff format .` — must be clean
6. Run: `pre-commit run --all-files` — must pass

### 1.5 — GitHub: Merge Phase 1
1. `git add . && git commit -m "feat(phase-1): data foundation — synthetic data + ingestion pipeline"`
2. `git push origin feature/phase-1-data-foundation`
3. Open PR → target: `develop`
4. Verify CI green (Ruff + pytest + Docker build)
5. Request review → approval → merge

> ✅ **Phase 1 complete** — CI green, tests pass, PR merged to `develop`.

---

## PHASE 2 — FEATURE ENGINEERING
> *Goal: Build the full PI-System-inspired feature pipeline.*

### 2.1 — Plan: Features *(Plan Step 2A — no code yet)*
1. Create branch: `git checkout -b feature/phase-2-feature-engineering`
2. Write plan outlining all features:
   - Rolling statistics: mean, std, kurtosis over 1h, 6h, 24h windows
   - Rate-of-change (delta) tags
   - Cross-sensor correlation tags (flow vs pressure)
   - CIP cycle detection features (reset fouling clock at each CIP)
   - NPD (Normalised Pressure Differential) as primary membrane-health proxy
   - tsfresh automated feature extraction
3. Present plan — **get approval**

### 2.2 — Implement
1. `src/features/rolling_stats.py` — Polars `group_by_dynamic` for time-window aggregations
2. `src/features/delta_tags.py` — rate-of-change features
3. `src/features/cross_sensor.py` — correlation features
4. `src/features/cip_detection.py` — CIP cycle detection from POC script
5. `src/features/npd.py` — NPD computation
6. `src/features/tsfresh_pipeline.py` — automated tsfresh extraction
7. Output: `data/processed/ro1a_features_v1.parquet`
8. Append Phase 2 entry to `RO_SDD.md`

> ⚠️ **NEVER use `.to_pandas()` or `read_parquet()` (eager). Always lazy frames + `group_by_dynamic()`.**

### 2.3 — 🔔 NOTIFY FOR TESTING
1. `tests/features/test_rolling_stats.py` — verify window calculations
2. `tests/features/test_npd.py` — Hypothesis tests: NPD always in valid range after cleaning
3. `tests/features/test_cip_detection.py` — verify CIP cycle boundary detection
4. Verify: NPD trend matches POC output (`scr_14_rul_cip_prediction.py`)
5. Run: `pytest tests/features/ -v` — all must pass
6. Run: `ruff check . && ruff format .`

### 2.4 — GitHub: Merge Phase 2
1. `git add . && git commit -m "feat(phase-2): feature engineering — NPD, CIP, rolling stats, tsfresh"`
2. `git push origin feature/phase-2-feature-engineering`
3. Open PR → target: `develop` → CI green → review → merge

> ✅ **Phase 2 complete** — CI green, NPD matches POC output, PR merged to `develop`.

---

## PHASE 3 — MODELLING
> *Goal: Train and evaluate RUL prediction models with full MLflow experiment tracking.*

### 3.1 — Plan: Model Selection *(Plan Step 3A — no code yet)*
1. Create branch: `git checkout -b feature/phase-3-modelling`
2. Write plan comparing:
   - Random Forest Regressor — baseline, client-explainable Feature Importance
   - XGBoost with time-series cross-validation
   - STUMPY Matrix Profile — unsupervised precursor detection
3. Define MLflow logging schema: params, RMSE, MAE, feature importances, training data hash
4. Define success criterion: RMSE ≤ 8 hours on held-out year-4 test set
5. Present plan — **get approval**

### 3.2 — Implement
1. Time-based train/test split: years 1–3 train, year 4 test (no random shuffle)
2. `src/models/baseline_rf.py` — Random Forest with Optuna hyperparameter tuning
3. `src/models/xgboost_model.py` — XGBoost with time-series cross-validation
4. `src/models/stumpy_profile.py` — STUMPY Matrix Profile anomaly detection
5. `src/models/online_river.py` — River incremental model for concept drift
6. Log all experiments to MLflow (URI from `config.py` / environment variable)
7. Log plain-language explanation of Feature Importance output
8. Append Phase 3 entry to `RO_SDD.md`

### 3.3 — 🔔 NOTIFY FOR TESTING
1. `tests/models/test_train_test_split.py` — verify no data leakage (time-based split)
2. `tests/models/test_mlflow_logging.py` — verify all required metrics are logged
3. Verify: best model RMSE ≤ 8 hours on year-4 test set (check MLflow UI)
4. Run: `pytest tests/models/ -v`
5. Run: `ruff check . && ruff format .`

### 3.4 — GitHub: Merge Phase 3
1. `git add . && git commit -m "feat(phase-3): modelling — RF, XGBoost, STUMPY, MLflow tracking"`
2. `git push origin feature/phase-3-modelling`
3. Open PR → target: `develop` → CI green → review → merge

> ✅ **Phase 3 complete** — RMSE ≤ 8h verified in MLflow, CI green, PR merged to `develop`.

---

## PHASE 4 — ALERT ENGINE
> *Goal: Build the rule-based alert threshold engine wired into the dashboard.*

### 4.1 — Plan: Alert Logic *(Plan Step 4A — no code yet)*
1. Create branch: `git checkout -b feature/phase-4-alerts`
2. Read `RO1A_working_Rules_v1.csv` — document all threshold rules
3. Design alert states: green / amber (72h warning) / red (24h critical) / CIP
4. Plan recommended corrective action text for each alert state
5. Present plan — **get approval**

### 4.2 — Implement
1. `src/alerts/threshold_engine.py` — rule-based thresholds from CSV
2. `src/alerts/alert_state.py` — `AlertState` enum: GREEN / AMBER / RED / CIP
3. `src/alerts/recommended_actions.py` — corrective action text per alert state
4. Wire alert engine output into `dashboard.py` — add traffic-light health indicator
5. Append Phase 4 entry to `RO_SDD.md`

### 4.3 — 🔔 NOTIFY FOR TESTING
1. `tests/alerts/test_thresholds.py` — test every boundary condition (72h, 24h, CIP)
2. `tests/alerts/test_alert_state.py` — verify correct state transitions
3. Verify: all rules from `RO1A_working_Rules_v1.csv` are covered by tests
4. Manual QA: run dashboard, verify traffic-light updates correctly with test data
5. Run: `pytest tests/alerts/ -v`
6. Run: `ruff check . && ruff format .`

### 4.4 — GitHub: Merge Phase 4
1. `git add . && git commit -m "feat(phase-4): alert engine — threshold rules, traffic-light dashboard"`
2. `git push origin feature/phase-4-alerts`
3. Open PR → target: `develop` → CI green → review → merge

> ✅ **Phase 4 complete** — All boundary conditions tested, dashboard QA passed, PR merged.

---

## PHASE 5 — CONTAINERISATION
> *Goal: Full stack runs inside Docker on Windows host, verified by CI.*

### 5.1 — Finalise Dockerfile
1. Create branch: `git checkout -b feature/phase-5-docker`
2. Finalise `Dockerfile`: Python 3.12 slim + all requirements
3. Add `MLFLOW_TRACKING_URI` environment variable
4. Add volume mounts for `data/` and `mlruns/` in `docker-compose.yml`
5. Verify `pathlib.PurePosixPath` used inside container code
6. Test: `docker-compose up --build` — all services start cleanly

### 5.2 — End-to-End Smoke Test in Docker
1. Run full pipeline inside container: ingestion → features → model → alerts
2. Verify MLflow UI at `localhost:5000`
3. Verify Streamlit dashboard at `localhost:8501`
4. Verify data written to `data/processed/` volume mount
5. Verify MLflow artefacts written to `mlruns/` volume mount

### 5.3 — 🔔 NOTIFY FOR TESTING
1. Verify GitHub Actions Docker build job passes for this branch
2. Test memory usage: full pipeline runs within 2 GB RAM (`memory_profiler`)
3. Test on a clean Docker environment — no "works on my machine" issues
4. Append Phase 5 entry to `RO_SDD.md`

### 5.4 — GitHub: Merge Phase 5
1. `git add . && git commit -m "feat(phase-5): Docker containerisation — full stack in container"`
2. `git push origin feature/phase-5-docker`
3. Open PR → target: `develop` → CI green (including Docker build job) → review → merge

> ✅ **Phase 5 complete** — Full stack in Docker, memory check passes, CI green, PR merged.

---

## PHASE 6 — RAG / LangChain / HuggingFace
> *Goal: Add plain-language alert explanations using local HuggingFace + LangChain RAG.*
> *The core prediction pipeline is NOT changed.*

### 6.1 — Plan: RAG Corpus & Chain *(no code yet)*
1. Create branch: `git checkout -b feature/phase-6-rag`
2. Plan RAG corpus:
   - `RO1A_working_Rules_v1.csv` — primary knowledge source
   - Phase logs from `RO_SDD.md`
   - Maintenance knowledge base (Markdown documents)
3. Plan LangChain chain:
   - Step 1: Embed alert context using `sentence-transformers/all-MiniLM-L6-v2`
   - Step 2: FAISS retrieval — find top-3 relevant rules from corpus
   - Step 3: LLM generates plain-language explanation combining alert + retrieved rules
4. Present plan — **get approval**

### 6.2 — Build RAG Corpus
1. `src/rag/corpus_builder.py` — LangChain document loaders for CSV + Markdown
2. `src/rag/embedder.py` — HuggingFace sentence-transformers embedding
3. Build FAISS index: `rag_index/ro1a_rules_index.faiss`
4. Add `HF_TOKEN` to Dockerfile environment (read from GitHub Secrets in CI)

### 6.3 — Build LangChain RAG Chain
1. `src/rag/rag_chain.py` — LangChain RAG chain: embed → retrieve → generate
2. `src/rag/explainer.py` — `RagExplainer` class wrapping the chain
3. Interface: `RagExplainer.explain(alert_state, sensor_readings) -> str`
4. Chain must be **stateless** — no session memory between alert invocations

### 6.4 — Integrate into Dashboard
1. Add explanation card to Streamlit dashboard — shows below alert panel
2. Explanation generated only when alert state is AMBER, RED, or CIP
3. Add loading spinner: "Generating explanation..." while RAG chain runs
4. Append Phase 6 entry to `RO_SDD.md`

### 6.5 — 🔔 NOTIFY FOR TESTING
1. `tests/rag/test_corpus.py` — verify all rules from CSV are indexed
2. `tests/rag/test_retrieval.py` — for known alert states, verify correct rules retrieved
3. `tests/rag/test_explainer.py` — verify explanation output is non-empty string with expected format
4. Verify: RAG failures do NOT propagate to or block the alert engine
5. Manual QA: test explanations for each alert level (AMBER, RED, CIP)
6. Run: `pytest tests/rag/ -v`
7. Run: `ruff check . && ruff format .`

### 6.6 — GitHub: Merge Phase 6
1. `git add . && git commit -m "feat(phase-6): RAG layer — HuggingFace + LangChain + FAISS alert explanations"`
2. `git push origin feature/phase-6-rag`
3. Open PR → target: `develop` → CI green → review → merge

> ✅ **Phase 6 complete** — Retrieval quality verified, explanation cards working, CI green, PR merged.

---

## PHASE 7 — PRODUCTION RELEASE
> *Goal: Merge everything to `main`, tag the release, final smoke test.*

### 7.1 — Final Pre-Release Check
1. Verify all success criteria from `Prod_prompt.md` Section 9 are met
2. Verify `RO_SDD.md` has a phase entry for every implemented phase
3. Verify `CLAUDE.md` is up to date with final architecture
4. Run: `pytest tests/ -v --cov=src --cov-report=term` — all pass, ≥80% coverage
5. Run full pipeline inside Docker end-to-end — no errors
6. Check MLflow: best model RMSE ≤ 8 hours is logged

### 7.2 — Merge `develop` to `main`
1. Open PR: `develop` → `main` on GitHub
2. CI must be fully green
3. Get final review approval
4. Merge

### 7.3 — Tag Release
1. `git checkout main && git pull`
2. `git tag -a v1.0.0 -m "Release v1.0.0 — ChainHomeAI RO Predictive Maintenance Platform"`
3. `git push origin v1.0.0`
4. Create GitHub Release from this tag with release notes

### 7.4 — Final Smoke Test
1. `docker-compose pull && docker-compose up`
2. Verify Streamlit at `localhost:8501`
3. Verify MLflow at `localhost:5000`
4. Trigger a test alert — verify full flow: sensor reading → alert → RAG explanation

> ✅ **PROJECT COMPLETE** — v1.0.0 released. All code on GitHub. CI/CD active. `main` protected.

---

## QUICK REFERENCE

### Daily Commands

| Action | Command |
|---|---|
| Activate venv | `.venv\Scripts\activate` |
| Lint check | `ruff check .` |
| Format | `ruff format .` |
| Run tests | `pytest tests/ -v` |
| Run tests + coverage | `pytest tests/ --cov=src --cov-fail-under=80` |
| Pre-commit (all files) | `pre-commit run --all-files` |
| Start Docker stack | `docker-compose up --build` |
| Create feature branch | `git checkout -b feature/phase-{N}-{name}` |
| Commit | `git commit -m "feat(phase-N): description"` |
| Push branch | `git push origin feature/phase-{N}-{name}` |

### Commit Message Format
```
feat(phase-1): short description of what was added
fix(phase-3): short description of what was fixed
test(phase-2): add Hypothesis tests for NPD invariants
ci: update GitHub Actions workflow
chore: update requirements.txt
docs: update RO_SDD.md phase log
```

### Testing Notification Checklist
Every time you see **🔔 NOTIFY FOR TESTING**:
1. Stop writing new features
2. Run: `pytest tests/ -v`
3. Run: `ruff check . && ruff format .`
4. Fix any failures
5. Only proceed when all tests pass and CI is green

### Phase Summary

| Phase | What You're Building | Key Test |
|---|---|---|
| 0 | GitHub repo, CI/CD, pre-commit, Docker base | CI pipeline runs on first push |
| 1 | Synthetic data generator + ingestion pipeline | Schema invariants + bad-data flagging |
| 2 | Feature engineering — NPD, CIP, rolling stats | NPD matches POC output |
| 3 | ML models — RF, XGBoost, STUMPY + MLflow | RMSE ≤ 8h on year-4 test set |
| 4 | Alert engine — threshold rules + dashboard | All boundary conditions covered |
| 5 | Docker containerisation — full stack | Full pipeline in < 2 GB RAM |
| 6 | RAG — HuggingFace + LangChain + FAISS | Correct rules retrieved per alert type |
| 7 | Production release — merge to `main`, tag v1.0.0 | End-to-end smoke test passes |

---

*DEV_GUIDE v1.0 | ChainHomeAI RO Predictive Maintenance | 2026-03-21*
