# JOBREADY_PLAN — ChainHomeAI RO Predictive Maintenance
## 5-Week US Job Readiness Plan — v1.1

> **Path:** `C:\chainhomeai\code\JOBREADY_PLAN.md`
> **Purpose:** Your master plan from first line of code to US job applications.
> **How to use:** Follow week by week. Tick every step as you complete it.

---

## HOW THIS WORKS

- **Claude Code** writes the code. **You** understand, approve, test, and explain it.
- After every phase Claude Code implements — **spend 30 minutes reading the code** before moving on. You must be able to explain every part in an interview.
- When you see **🔔 NOTIFY FOR TESTING** — stop, run all tests, fix failures before continuing.
- All code goes through GitHub — basic commits at minimum, even without full CI/CD.
- **Never skip the PLAN step** — Claude Code works in PLAN MODE first, you approve, then it implements.

---

## WEEK 1 — BUILD THE CORE PIPELINE
> *Goal: Synthetic data generated, ingestion pipeline working, features engineered.*
> *Claude Code does the implementation. You understand every step.*

### Day 1 — Repo + Environment Setup

**Step 1 — GitHub**
1. Go to github.com → New Repository
2. Name: `chainhomeai-ro` → Private → tick "Add README" → Create
3. Click the green Code button → copy the HTTPS URL
4. Open terminal on your Windows machine: `git clone https://github.com/yourname/chainhomeai-ro.git`

**Step 2 — Folder Structure**

Create this exact structure on your machine at `C:\chainhomeai\`:
```
C:\chainhomeai\
├── code\
│   ├── poc\
│   ├── src\
│   │   ├── ingestion\
│   │   ├── features\
│   │   ├── models\
│   │   ├── alerts\
│   │   ├── tags\
│   │   ├── rag\
│   │   └── dashboard\
│   ├── tests\
│   │   ├── ingestion\
│   │   ├── features\
│   │   ├── models\
│   │   ├── alerts\
│   │   └── rag\
│   └── data\
│       ├── raw\
│       ├── synthetic\
│       └── processed\
└── docs\
```

**Step 3 — Copy Documents**

Copy these files into `C:\chainhomeai\code\`:
- `Prod_prompt.md`
- `CLAUDE.md`
- `RO_SDD.md`
- `JOBREADY_PLAN.md` ← this file

Copy this file into `C:\chainhomeai\docs\`:
- `RO1A_working_Rules_v1.csv`

Copy your POC files into `C:\chainhomeai\code\poc\`:
- `scr_14_rul_cip_prediction.py`
- `dashboard.py`

**Step 4 — Python Environment**
1. Verify Python 3.12 is installed: `python --version`
2. If not installed: download from python.org → install → verify
3. Open terminal, navigate to code folder: `cd C:\chainhomeai\code`
4. Create virtual environment: `python -m venv .venv`
5. Activate it: `.venv\Scripts\activate`
6. You should see `(.venv)` appear at the start of your terminal prompt

**Step 5 — Create requirements.txt**

Create a file called `requirements.txt` in `C:\chainhomeai\code\` with these contents:
```
polars
duckdb
pydantic
tsfresh
stumpy
scikit-learn
xgboost
river
optuna
mlflow
ruff
pytest
hypothesis
pytest-cov
streamlit
```

**Step 6 — Install dependencies**
1. `pip install -r requirements.txt`
2. This will take a few minutes — let it run
3. Verify Ruff is working: `ruff check .` — should return clean on empty project

**Step 7 — First commit**
```
git add .
git commit -m "chore: initial repo setup"
git push
```
Go to github.com and verify your files are visible in the repository.

> ✅ **Day 1 done** — Repo live on GitHub, folder structure created, environment working, all documents in place.

---

### Days 2-3 — Synthetic Data + Ingestion Pipeline (Phase 1)

**Day 2 — Plan + Implement**
1. Open Claude Code → paste the full contents of `Prod_prompt.md` to orient it
2. Ask Claude Code for **Plan Step 1A** — synthetic data generation strategy. Review and approve.
3. Ask Claude Code for **Plan Step 1B** — ingestion pipeline logic. Review and approve.
4. Ask Claude Code to implement Phase 1:
   - `src/ingestion/synthetic_data.py`
   - `src/tags/tag_registry.py`
   - `src/ingestion/ingest.py`
   - `src/ingestion/data_quality.py`
5. Verify output Parquet files appear in `data/synthetic/`

**Day 3 — Understand + Test**
1. Read every file Claude Code produced — ask me to explain anything unclear
2. Be able to answer: *"Why do you keep bad sensor data in the raw dataset?"*
3. Be able to answer: *"What does TagRegistry do and why is it inspired by PI System?"*

### 🔔 NOTIFY FOR TESTING — Phase 1
1. Run: `pytest tests/ingestion/ -v` — all must pass
2. Run: `ruff check . && ruff format .` — must be clean
3. `git add . && git commit -m "feat(phase-1): data foundation" && git push`

> ✅ **Days 2-3 done** — Synthetic dataset generated, ingestion pipeline validated.

---

### Days 4-5 — Feature Engineering (Phase 2)

**Day 4 — Plan + Implement**
1. Ask Claude Code for **Plan Step 2A** — feature outline. Review and approve.
2. Ask Claude Code to implement:
   - `src/features/rolling_stats.py`
   - `src/features/delta_tags.py`
   - `src/features/cip_detection.py`
   - `src/features/npd.py`
   - `src/features/tsfresh_pipeline.py`
3. Verify `data/processed/ro1a_features_v1.parquet` is produced

**Day 5 — Understand + Test**
1. Read the feature files — ask me to explain anything unclear
2. Be able to answer: *"What is NPD and why is it the primary membrane health indicator?"*
3. Be able to answer: *"Why do you compute features relative to last CIP, not absolute time?"*
4. Be able to answer: *"What does tsfresh do that you couldn't do manually?"*

### 🔔 NOTIFY FOR TESTING — Phase 2
1. Run: `pytest tests/features/ -v` — all must pass
2. Verify NPD trend matches POC output from `scr_14_rul_cip_prediction.py`
3. Run: `ruff check .`
4. `git add . && git commit -m "feat(phase-2): feature engineering" && git push`

> ✅ **Days 4-5 done** — Full feature pipeline working, NPD matches POC.

---

### Days 6-7 — Buffer + Review
1. Catch up on anything that slipped during the week
2. Run full pipeline end-to-end: raw data → features
3. Review all code produced so far — make sure you can explain every file
4. Ask me any questions about the technology choices
5. `git add . && git commit -m "chore: week 1 wrap-up" && git push`

> ✅ **Week 1 done** — Data pipeline and feature engineering complete and understood.

---

## WEEK 2 — ML + ALERTS + DASHBOARD + DOCKER + RAG
> *Goal: Full working system — predictions, alerts, dashboard, containerised, with RAG explanations.*
> *This is the heavy week. Claude Code carries the implementation load.*

### Days 1-2 — Modelling (Phase 3)

**Day 1 — Plan + Implement**
1. Ask Claude Code for **Plan Step 3A** — model comparison plan. Review and approve.
2. Ask Claude Code to implement:
   - `src/models/baseline_rf.py` — Random Forest + Optuna
   - `src/models/xgboost_model.py` — XGBoost
   - `src/models/stumpy_profile.py` — Matrix Profile
   - `src/models/online_river.py` — River incremental model
3. Verify MLflow UI at `localhost:5000` shows experiment runs

**Day 2 — Understand + Test**
1. Open MLflow UI — verify RMSE ≤ 8 hours on year-4 test set
2. Be able to answer: *"Why Random Forest as baseline and XGBoost as main model?"*
3. Be able to answer: *"What is STUMPY doing that XGBoost cannot?"*
4. Be able to answer: *"What is concept drift and why does River handle it?"*

### 🔔 NOTIFY FOR TESTING — Phase 3
1. Run: `pytest tests/models/ -v`
2. Verify best model RMSE ≤ 8h logged in MLflow
3. `git add . && git commit -m "feat(phase-3): modelling + MLflow" && git push`

> ✅ **Days 1-2 done** — Models trained, RMSE target met, MLflow tracking working.

---

### Day 3 — Alert Engine + Dashboard (Phase 4)
1. Ask Claude Code for **Plan Step 4A** — alert logic. Review and approve.
2. Implement:
   - `src/alerts/threshold_engine.py`
   - `src/alerts/alert_state.py`
   - `src/alerts/recommended_actions.py`
   - Wire into Streamlit dashboard
3. Run dashboard: `streamlit run src/dashboard/app.py`
4. Manually verify traffic-light updates correctly for GREEN / AMBER / RED / CIP states
5. Be able to answer: *"Why are the thresholds 10% and 15% deviation from baseline?"*

### 🔔 NOTIFY FOR TESTING — Phase 4
1. Run: `pytest tests/alerts/ -v` — all boundary conditions must pass
2. Manual QA: dashboard shows correct alert for each state
3. `git add . && git commit -m "feat(phase-4): alert engine + dashboard" && git push`

> ✅ **Day 3 done** — Alerts working, dashboard showing health score + RUL + recommended action.

---

### Day 4 — Docker (Phase 5)
1. Ask Claude Code to implement `Dockerfile` + `docker-compose.yml`
2. Run: `docker-compose up --build`
3. Verify:
   - Streamlit at `localhost:8501`
   - MLflow at `localhost:5000`
   - Data volumes mounted correctly
4. Run full pipeline inside container — verify no errors
5. Be able to answer: *"Why Docker? Why not just run it natively?"*
6. `git add . && git commit -m "feat(phase-5): Docker containerisation" && git push`

> ✅ **Day 4 done** — Full stack running in Docker.

---

### Days 5-6 — RAG Layer (Phase 6)

**Day 5 — Plan + Corpus**
1. Ask Claude Code for **Plan Step 6A** — RAG corpus + chain plan. Review and approve.
2. Implement:
   - `src/rag/corpus_builder.py` — load `RO1A_working_Rules_v1.csv` + docs
   - `src/rag/embedder.py` — HuggingFace embeddings
   - Build FAISS index: `rag_index/ro1a_rules_index.faiss`

**Day 6 — Chain + Dashboard Integration**
1. Implement:
   - `src/rag/rag_chain.py` — LangChain RAG chain
   - `src/rag/explainer.py` — `RagExplainer` class
2. Integrate explanation card into Streamlit dashboard
3. Test manually: trigger AMBER, RED, CIP alerts — verify explanation text appears
4. Be able to answer: *"What is RAG and why use it instead of hardcoding responses?"*
5. Be able to answer: *"Why is the RAG layer separate from the prediction pipeline?"*

### 🔔 NOTIFY FOR TESTING — Phase 6
1. Run: `pytest tests/rag/ -v`
2. Verify RAG failure does NOT block the alert engine
3. `git add . && git commit -m "feat(phase-6): RAG layer — HuggingFace + LangChain + FAISS" && git push`

> ✅ **Days 5-6 done** — Plain-language explanations appearing on dashboard alerts.

---

### Day 7 — End-to-End Test + Buffer
1. Run complete pipeline inside Docker from raw data to dashboard
2. Trigger all alert levels — verify: sensor → prediction → alert → RAG explanation
3. Fix any gaps or rough edges
4. Catch up on anything that slipped during the week
5. `git add . && git commit -m "chore: week 2 wrap-up, end-to-end verified" && git push`

> ✅ **Week 2 done** — Full working system. Every component built and understood.

---

## WEEK 3 — 3 DAYS ONLY — POLISH + GITHUB + LINKEDIN
> *Goal: Project is publicly presentable. Anyone can look at your GitHub and understand what you built.*

### Day 1 — GitHub Polish
1. Review all code for obvious rough edges — ask Claude Code to clean up anything messy
2. Write `README.md` — must include:
   - What the system does (1 paragraph, plain English)
   - Architecture diagram (copy pipeline diagram from `CLAUDE.md`)
   - Tech stack list
   - How to run it (`docker-compose up`)
   - Screenshot of the Streamlit dashboard
   - Results — RMSE achieved, alert levels demonstrated
3. Make repo **public** on GitHub
4. `git add . && git commit -m "docs: README and project polish" && git push`

### Day 2 — Project Write-Up
1. Write a 1-page project summary for job applications and recruiters:
   - **Problem:** RO membrane failure in water treatment plants
   - **Solution:** ML pipeline predicting failure 12–72 hours ahead
   - **Tech:** Python, Polars, XGBoost, MLflow, LangChain, HuggingFace, Docker
   - **Results:** RMSE ≤ 8h on held-out test set, RAG-powered plain-language alerts
   - **Impact:** Prevents unplanned downtime, enables proactive maintenance scheduling
2. Practice a 5-minute verbal walkthrough of the project out loud

### Day 3 — LinkedIn + Job Boards
1. Update LinkedIn:
   - Add project to Experience or Projects section
   - Update headline: `ML Engineer | Predictive Maintenance | Python · XGBoost · LangChain · Docker`
   - Add skills: Python, Machine Learning, MLflow, LangChain, HuggingFace, Docker, Streamlit
2. Set up job alerts on LinkedIn and Indeed:
   - Search: `ML engineer predictive maintenance`, `MLOps engineer manufacturing`, `AI engineer industrial`
   - Locations: Remote + Texas + California + Washington

> ✅ **Week 3 done** — Project on GitHub, LinkedIn updated, job alerts active.

---

## WEEK 4 — INTERVIEW PREP
> *Goal: Walk into any ML engineer interview and confidently discuss your project and core concepts.*

### Days 1-2 — ML Fundamentals
Study by relating every concept back to ChainHomeAI:

1. **Bias-variance tradeoff** — why did you tune XGBoost with Optuna?
2. **Overfitting** — why time-based train/test split and not random shuffle?
3. **Feature importance** — what does Random Forest tell you about which sensors matter most?
4. **Cross-validation** — how did you validate your time-series model?
5. **Precision vs recall** — in predictive maintenance, which matters more and why?
6. **Concept drift** — what is it, and why did you add River for online learning?
7. **Anomaly detection** — what is STUMPY doing, and how does Matrix Profile work?
8. **RAG** — explain the full chain: embed → retrieve → generate. Why FAISS?

> Ask me to quiz you on any of these. Practice out loud, not just in your head.

### Days 3-4 — System Design
Practice answering this question out loud:
> *"Design a predictive maintenance system for 500 RO plants across the US."*

Structure your answer around:
1. Data ingestion at scale — how does your Polars pipeline extend?
2. Feature engineering — how do you handle 500 plants in parallel?
3. Model serving — how do you serve predictions in real time?
4. Alerting — how do you ensure no alert is missed?
5. Monitoring — how do you detect model drift across 500 plants?
6. RAG at scale — shared knowledge base vs plant-specific?

> You already built the single-plant version. Extending it to scale is the interview answer.

### Days 5-6 — Python Coding Practice
Focus on practical data problems — not algorithms:

1. Write a rolling mean function without any libraries — pure Python lists
2. Implement a simple linear regression from scratch
3. Given a time-series list, detect anomalies using z-score
4. Write a function that splits time-series data into train/test without shuffling
5. Explain line by line what your `compute_npd_rolling()` function does

### Day 7 — Mock Interview
Ask me to conduct a full mock interview:
1. *"Walk me through your ChainHomeAI project"* — 5 minutes, no notes
2. *"Why XGBoost over a neural network for this problem?"*
3. *"How would you handle a sensor that goes offline for 3 days?"*
4. *"Design the monitoring system for when this goes to production"*
5. *"What would you do differently if you had 6 months instead of 2 weeks?"*

> ✅ **Week 4 done** — Interview ready. Start applying.

---

## WEEK 5 ONWARDS — DEVOPS (coached separately)
Once you have interviews lined up, add the full DevOps layer:
- GitHub Actions CI/CD pipeline
- Branch protection rules + pre-commit hooks
- Cloud deployment (AWS or Azure)

> This is the difference between getting hired and getting hired at a significantly higher salary.

---

## QUICK REFERENCE

### The 3 Questions You Must Nail in Every Interview
1. *"Walk me through your project"* — 5 minutes, clear, confident, no jargon
2. *"Why did you choose [any technology]?"* — you have a reason for every single choice
3. *"How would this scale?"* — you've thought about 500 plants, not just 1

### Your Tech Stack for LinkedIn / Resume
```
Python 3.12 · Polars · XGBoost · Scikit-learn · STUMPY · tsfresh · MLflow · Optuna · LangChain · HuggingFace · FAISS · Streamlit · Docker · GitHub
```

### Target Job Titles
- ML Engineer — Predictive Maintenance
- MLOps Engineer — Manufacturing / Industrial
- AI Engineer — Industrial IoT
- Data Scientist — Asset Management
- Senior Data Scientist — Water / Utilities

### Daily Commit Command
```
git add .
git commit -m "feat(phase-N): short description of what was done"
git push
```

### After Each Phase — 30-Minute Rule
After Claude Code implements anything — before moving on:
1. Read the code Claude Code produced
2. Ask me to explain anything you don't understand
3. Confirm you can explain it out loud without notes
4. Only then move to the next phase

---

*JOBREADY_PLAN v1.1 | ChainHomeAI RO Predictive Maintenance | 2026-03-21*
