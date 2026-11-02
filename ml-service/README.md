# ML Service

Trains and serves the predictive models behind the academic-monitoring platform: a forward-looking academic "index" for each student, three risk classifiers, and short-horizon index forecasts. Reads its features from `import-service` over HTTP.

## Models

All models are XGBoost, trained per (student, semester) row:

| Purpose | Type | Predicts                                                                                                                                                       |
|---|---|----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `index_regression` | regression | Student's academic index **next semester**, from this semester's behavior - a forward-looking "how are they trending" score, not a snapshot of current grades. |
| `expulsion_classifier` | classification | Whether the student disappears next semester.                                                                                                                  |
| `debt_classifier` | classification | Whether the student ends up repeating a subject next semester.                                                                                                 |
| `admission_classifier` | classification | Whether the student is denied exam admission **this** semester (a same-semester threshold status, not a forecast - critical absence or a failing average).     |
| `index_forecast_horizon_2` / `_3` | regression | Index 2 / 3 semesters ahead.                                                                                                                                   |

Features include current-semester grades/attendance, deltas vs. the previous semester, and cumulative to-date summaries. `admission_classifier` excludes the cumulative features (they're redundant with - not independent of - the same-semester values its label is computed from).

## The academic index

`TargetCalculator.calculate_target` scores one semester on a 0-100 scale (higher is better) as a weighted average of 0-100 sub-scores, so every term is a **rate**, not a raw count:

| Sub-score | Weight | Computed from |
|---|---|---|
| grades | 0.45 | `avg_grade` |
| attendance | 0.20 | 100 − (0.4·lecture + 0.6·lab absence %) |
| submissions | 0.15 | 100 − missing / gradable sessions % |
| unworked absences | 0.10 | 100 − unworked absences / sessions % |
| punctuality | 0.05 | 100 − late / gradable sessions % |
| consistency | 0.05 | 100 − 2·`grade_stddev` |

A full-time student over the critical absence threshold (75%) is capped at 20. A student who has dropped out by the target semester gets 0 (`build_horizon_dataset`). The score uses only the target semester's own data - `disappeared_next_semester` and `repeated_subjects_count` describe the *following* semester and are the classifiers' job.

Categories: `high` ≥ 70, `medium` ≥ 40, `low` below. On the synthetic data, normal students average ~83, debt-risk ~67, expulsion-risk ~55 and admission-risk students sit at the cap.

## Label windows

Each classifier declares when its label becomes observable (`LabelWindow` in `target_calculator.py`), and rows whose label is not observable yet are left out of training:

- `admission_classifier` - `current_semester`: every row.
- `expulsion_classifier` - `next_semester`: drops rows from the last semester in the data (nobody knows yet who leaves after it). A dropout's own last row is kept - it is the positive example.
- `debt_classifier` - `next_semester_enrolled`: also drops rows of students who left, since a subject can only be repeated by someone still enrolled.

## Evaluation split

The 80/20 split is by **student** (`StratifiedGroupKFold` for classifiers, `GroupShuffleSplit` for regressions): every row of a student is either in train or in test, so the test metrics measure generalisation to unseen students, not recognition of a student already seen in another semester.

## Monotone constraints

Grades, absence and submission features are strongly correlated, and unconstrained trees split credit between them arbitrarily - on the synthetic data the explanations claimed that *more* missing submissions raised the index and lowered the expulsion risk, the opposite of what the data shows. Every model is therefore trained with XGBoost `monotone_constraints` from `FeatureEncoder.monotone_constraints_for`: the index can only rise with grades and only fall with absence / unworked absences / missing and late submissions / grade spread, and the risk classifiers get the opposite directions. Deltas, `course_year`, study mode and `semesters_completed_count` stay unconstrained. This costs little (index r2 actually went up slightly, expulsion f1 dropped ~0.04) and guarantees that an explanation never points the wrong way.

Warm-starting from a model trained without these constraints would mix unconstrained trees back in, so after this change the ML database and `trained_models/` must be reset.

## Explanations

Every prediction stores its top-5 SHAP contributions (`shap_contributions.top_contributions`): `index_explanations` for the index, `risk_explanations` for each risk assessment (log-odds contributions, so positive means "pushes the risk up"). Both are returned by `/student-indexes/{id}/latest/full`.

SHAP runs in **interventional** mode against a background of 100 students sampled (deterministically) from the students being scored, so each contribution reads "compared to a typical current student". Combined with the monotone constraints this keeps explanations consistent: a higher absence or more missing submissions can only ever push the index down / the risk up. The default path-dependent mode compares against a "typical student on the same tree branch" instead, and on correlated features it produced contributions that moved the wrong way as a feature grew. Interventional SHAP costs ~2-3 s per model for ~1,400 students.

## Model lifecycle

Every training run is auto-versioned (`v1`, `v2`, ...) per purpose. A new version only becomes active if it beats the currently active one on its purpose's metric (`r2` for regressions, `f1` for classifiers) — otherwise it's kept on disk (for a bounded number of recent versions, see `KEEP_INACTIVE_MODEL_VERSIONS`) but not promoted. Training also warm-starts from the currently active model when one exists, adding a small number of boosting rounds on top rather than always starting from scratch.

See `services/model_promotion_service.py`.

## Stack

FastAPI + SQLAlchemy + PostgreSQL + XGBoost + SHAP (for per-prediction feature explanations).

## Setup

1. Start the database (from the repo root):
   ```bash
   docker compose up -d postgres-ml
   ```
2. Env vars this service reads (see repo root `.env`):
   - `DB_USER_ML_SERVICE`, `DB_PASSWORD_ML_SERVICE`, `DB_HOST_ML_SERVICE`, `DB_PORT_ML_SERVICE`, `DB_NAME_ML_SERVICE`
   - `IMPORT_SERVICE_URL` — base URL of `import-service` (required)
   - `ML_SERVICE_PORT` (default `8002`)
   - `KEEP_INACTIVE_MODEL_VERSIONS` (default `5`) — how many superseded model versions to keep on disk per purpose, for future warm-starting
3. Install dependencies (from the repo root, `uv` workspace):
   ```bash
   uv sync
   ```
4. Run the service:
   ```bash
   uv run ml-service
   ```
   or `uvicorn ml_service.main:app --reload --port 8002`.

`import-service` must be running and reachable at `IMPORT_SERVICE_URL` before training or inference.

## API

Training and inference take minutes on real data, so they run as **background jobs** and the caller polls for the outcome:

- `POST /training/jobs` - starts training all 6 models against the latest data from `import-service`. Returns `202` with the job (`status: "queued"`) immediately. Optional body `{"requested_by": <user id>}` - the BFF passes the user who triggered it.
- `POST /inference/jobs` - starts scoring every student enrolled in the latest semester of the data, using whichever model version is currently active per purpose. Students who are no longer enrolled (dropped out) are skipped - their last index stays in the history, but they get no new "current" index or risks.
- `GET /training/jobs/{job_id}`, `GET /inference/jobs/{job_id}` - poll a job: `status` is `queued` → `running` → `succeeded` / `failed`, with `started_at`, `finished_at`, and either `result` or `error`. A training `result` holds per-model metrics, `promoted` (whether the version became active) and `warning` (why not); an inference `result` holds `processed`.
- `GET /training/jobs/latest`, `GET /inference/jobs/latest` - the most recent job of that type, e.g. so a reloaded page can see a job still running.

Only one job of each type can be active at a time (a partial unique index on `ml_jobs` enforces it, even across processes); a second `POST` gets `409` with the active job in `detail.job`. Training and inference don't block each other - inference keeps using the models that were active when it started. Jobs run in a thread of the ml-service process with their own database sessions; on startup any job still `queued`/`running` (the process died mid-job) is marked `failed`. When RabbitMQ arrives, the same jobs can be started by a queue consumer instead, without changing this API.
- `GET /student-indexes/{student_id}/latest/full` - a student's latest index, SHAP explanations, raw feature snapshot, risk assessments, and forecasts, all in one response.
- `GET /student-indexes/{student_id}/history` - index history for a student.
- `GET /model-versions/` - all trained model versions and their metrics/active status.
- `GET /test-import-semester-connection` - connectivity check against `import-service`.

## Tests

```bash
uv run pytest ml-service/tests
```