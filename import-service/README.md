# Import Service

Ingests and serves academic records (students, groups, teachers, subjects, enrollments, attendance, grades) for the academic-monitoring platform, and computes the per-semester feature snapshots that `ml-service` trains and predicts on.

Also includes a synthetic data generator, used for local development and testing in the absence of a real data source.

## Stack

FastAPI + SQLAlchemy + PostgreSQL.

## Setup

1. Start the database (from the repo root):
   ```bash
   docker compose up -d postgres
   ```
2. Copy `.env` values (see repo root `.env`) — this service reads:
   - `DB_USER_IMPORT_SERVICE`, `DB_PASSWORD_IMPORT_SERVICE`, `DB_HOST_IMPORT_SERVICE`, `DB_PORT_IMPORT_SERVICE`, `DB_NAME_IMPORT_SERVICE`
   - `IMPORT_SERVICE_PORT` (default `8001`)


3. Install dependencies (from the repo root, this is a `uv` workspace member):
   ```bash
   uv sync
   ```
4. Run the service:
   ```bash
   uv run import-service
   ```
   or `uvicorn import_service.main:app --reload --port 8001`.

Tables are created automatically on startup (`Base.metadata.create_all`) — there is no migration tool, so a schema change requires dropping and recreating the database.

## Generating synthetic data

```bash
python -m import_service.generator.generate_csv   # writes CSVs to import-service/data/
python -m import_service.importer                  # imports those CSVs into the database
```

The generator (`generator/config.py`, `generator/generate_csv.py`) creates a cohort of students with hidden "risk profiles" (normal / admission risk / debt risk / expulsion risk) that drive realistic, correlated grade/attendance/dropout patterns - without writing the profile itself to the output data, so downstream ML has to learn it from behavior.

Academic debt is not tied to a profile: every enrollment gets a hidden per-subject score level (the student's semester level plus noise) that the subject's grades are drawn around. A subject whose level is below `PASS_SCORE` is failed, and a failed subject is retaken next semester with probability `RETAKE_PROBABILITY_IF_FAILED` (otherwise the debt was closed on a re-exam, which leaves no trace). So any student can end up with a debt; weaker profiles just fail more often (on a typical run ~12% of normal students' semesters vs. ~65-85% for the at-risk profiles).

Each profile also has a `missing_submission_probability` (drifting per semester): some lab and control submissions simply have no grade, which is what `missing_submissions_count` measures. Exams are always graded.

The whole population is a single cohort that starts year 1 in the first generated academic year, so every group's `course_year` is the cohort's *current* year (`COHORT_CURRENT_COURSE_YEAR`).

## `course_year` semantics

`groups.course_year` is the group's course year **as of the latest academic year in the data**. The feature endpoint derives each semester's own course year by counting back (`course_year_at`): a group in year 3 in 2025/2026 was in year 2 in 2024/2025. Real imports must follow the same convention.

## API

- `students`, `groups`, `teachers`, `semesters`, `subjects`, `subject_offerings`, `class_sessions` - CRUD-style read endpoints for the raw academic records.
- `student-features/by-semester` - the main ML-facing endpoint. Returns one row per (student, semester): current-semester grades/attendance, deltas vs. the previous semester, and cumulative to-date summaries This is what `ml-service` trains and predicts on.

## Tests

```bash
uv run pytest import-service/tests
```

Covers the generator's data-integrity invariants (no accidental subject repeats between semesters, every retake follows a failed subject and not every failure is retaken, dropout never removes a student's first semester, missing submissions exist and depend on the profile, etc.) and the per-semester `course_year` derivation.
