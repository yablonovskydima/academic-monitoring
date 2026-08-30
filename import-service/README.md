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

## API

- `students`, `groups`, `teachers`, `semesters`, `subjects`, `subject_offerings`, `class_sessions` - CRUD-style read endpoints for the raw academic records.
- `student-features/by-semester` - the main ML-facing endpoint. Returns one row per (student, semester): current-semester grades/attendance, deltas vs. the previous semester, and cumulative to-date summaries This is what `ml-service` trains and predicts on.

## Tests

```bash
uv run pytest import-service/tests
```

Covers the generator's data-integrity invariants (no accidental subject repeats between semesters, dropout never removes a student's first semester, etc.)
