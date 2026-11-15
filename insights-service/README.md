# Insights Service

Turns ml-service output into something a curator can read and act on. A SHAP value next to a feature name is not a deliverable to a human; this service is where it becomes "Lab absences: 34% — higher than 85% of students. Discuss the reasons for the absences and agree on making up the missed classes."

Current state: domain logic, persistence, the ingestion API that ml-service calls after every finished inference run, and read endpoints for the BFF.

## API

- `POST /insight-runs/` - body `InsightRunCreate`: `source_job_id` (the ml-service inference job id) and one prediction per student (`student_id`, `group_id`, `semester_id`, `student_index_id`, `index_value`, `index_category`, raw `features`, `index_contributions`, `risks[]` with `risk_type`, `probability`, `contributions`, and `forecasts[]` with `semesters_ahead`, `predicted_index_value`). Forecasts are stored with the run, so the BFF reads the whole current state - index, risks, reasons, forecasts - from one place and one run, never mixing a newer ml-service number with an older explanation. Returns `201` with the stored run, or `200` with the already stored run when the same `source_job_id` is sent again (safe to retry / re-deliver). `422` on an invalid body.
- `GET /insight-runs/latest`, `GET /insight-runs/{run_id}`.
- `GET /health`.

Read endpoints for the BFF. insights-service does not know about users: the BFF resolves the caller's scope (curator → `group_ids`, dean → the groups of their faculties, admin → everything) and passes it as filters. Every "current" response names the run it comes from (`run.id`, `run.created_at`) so the UI can show when the data was last updated; before the first run they return `run: null` and empty lists, not `404`.

- `GET /student-insights/current?group_ids=&student_ids=&limit=50&offset=0` - the latest run's students, lowest index first: headline, index, category and each risk's level (no reasons - that is the card). `total` is the count before paging; `limit` ≤ 500.
- `GET /student-insights/{student_id}` - the student card: headline, index reasons, risks with their reasons, forecasts, and `is_current` (`false` when the student is missing from the latest run - the last known card is returned, marked as stale). `404` if the student was never in a run.
- `GET /student-insights/{student_id}/history?limit=20` - the student's insights per run, newest first.
- `GET /student-insights/{student_id}/changes?limit=50` - the student's changes between runs, newest first.
- `GET /insight-changes/latest?worsened_only=false&group_ids=` - changes detected by the latest run.
- `GET /group-summaries/latest?group_ids=` - per-group summaries of the latest run.

Send the **full** SHAP vector per prediction, not ml-service's stored top 5 (see below). That is ~8 KB per student as JSON - about 11 MB for the 1,400-student synthetic run, ~80 MB for 10,000 students. Fine for now; at that size switch to a gzip-compressed body or send `{feature_name: shap_value}` maps instead of objects (the feature values are already in `features`).

## What it does with one inference run

`InsightRunService.process_run` takes every student's prediction (index, three risks, SHAP contributions, raw feature snapshot) and stores:

- **Student insight** - `is_current` (whether it belongs to the latest run: a student missing from the latest run keeps the last known insight, marked as not current), a headline ("High risk of expulsion. Main reason: attendance"), the index reasons, and per risk a level and its reasons.
- **Changes** against the previous run - "Risk of expulsion: moderate → high", "Exam admission: admitted → near the threshold" - each `worsened` or `improved`. This is what the notification service will be built on.
- **Group summaries** - per group: index categories, students with a high risk per type, how many need attention, how many worsened, and the most common main reason.

Processing is idempotent per `source_job_id` (the ml-service inference job): a re-delivered run returns the already stored one.

## How reasons are built (`insights/`)

- `feature_catalog.py` - every ml-service feature gets a human-readable label, unit, **theme** (grades, attendance, submissions, trend, context) and whether higher is worse. Unknown features fall into `context` and are ignored, so a new ml-service feature never breaks a run.
- `reasons.py` - SHAP contributions are summed per theme (four absence features are one reason, not four), themes are ranked by their share of the total, and the strongest feature pointing the same way leads the text. Strength is `main` (≥ 50% of the total), `significant` (≥ 25%) or `minor`; themes below 10% and `context` (course year, study mode) are never shown as reasons. Values are compared with the other students of the run ("higher than 85% of students") instead of showing SHAP numbers. A trend reason is dropped when the change points the other way (unconstrained delta features can do that) or is too small to matter (`min_change`: 3 grade points, 5 p.p. of absence, 2 submissions).
- `risk_levels.py` - forecasts (expulsion, academic debt) map the probability to `low` / `moderate` (≥ 0.35) / `high` (≥ 0.65). ml-service probabilities are not calibrated (`scale_pos_weight`), so they are never shown as "a 31% chance". A level above `low` is only kept when the explanation has at least one risk reason (`supported_level`): an uncalibrated 0.36 for a student whose every reason is protective is just the population's base rate, and "moderate risk - because your absences are 0%" would contradict itself. Calibrating the probabilities in ml-service is the real fix. **Exam admission is a status, not a forecast**, and is explained by the rule itself: "Lecture absences: 78% — admission threshold is 75%", with `moderate` when a student is within 10 p.p. / 5 points of the threshold. The thresholds (`ADMISSION_ABSENCE_THRESHOLD`, `ADMISSION_GRADE_THRESHOLD`) come from the shared `.env` that ml-service reads too, so both services always apply the same rule; insights-service picks a change up on restart, ml-service only after retraining.
- `headlines.py`, `changes.py`, `group_summaries.py` - the headline, run-to-run changes and group aggregates.

## Why the full SHAP vector

Reasons are built from per-theme sums, and four attendance features or four submission features each contribute a little - the top 5 drops exactly those. Measured on the synthetic run (1,400 students), building reasons from the top 5 instead of all 20 contributions:

| Target | top 5 covers of total \|SHAP\| | main reason's theme differs | "has a risk reason" flips |
|---|---|---|---|
| index | 76% | 12% | 2% |
| expulsion | 78% | 17% | 13% |
| academic debt | 92% | 2% | 3% |
| exam admission | 86% | 4% | 8% |

The last column also changes the risk level (`supported_level`). ml-service already computes the full vector at inference time and only truncates it for storage, so the fix is to send everything in the request; its own top-5 tables can stay as they are.

## Setup

```bash
docker compose up -d postgres-insights
uv sync --all-packages
```

Env vars: `DB_*_INSIGHTS_SERVICE` (see `.env.example`), plus optional thresholds listed there.

## Tests

```bash
uv run pytest insights-service/tests
```
