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

- `POST /training/train` - trains all 6 models against the latest data from `import-service` and returns per-model metrics, `promoted` (whether this version became active), and `warning` (why not, if it didn't).
- `POST /inference/predict-all` - scores every student using their latest semester's features, using whichever model version is currently active per purpose.
- `GET /student-indexes/{student_id}/latest/full` - a student's latest index, SHAP explanations, raw feature snapshot, risk assessments, and forecasts, all in one response.
- `GET /student-indexes/{student_id}/history` - index history for a student.
- `GET /model-versions/` - all trained model versions and their metrics/active status.
- `GET /test-import-semester-connection` - connectivity check against `import-service`.

## Tests

```bash
uv run pytest ml-service/tests
```