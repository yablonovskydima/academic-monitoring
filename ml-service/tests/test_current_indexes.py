from datetime import date, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ml_service.controllers import student_indexes
from ml_service.database import Base, get_db
from ml_service.models import (  # noqa: F401
    feature_snapshot, index_explanation, index_forecast, risk_assessment, risk_explanation,
)
from ml_service.models.ml_job import MLJob, MLJobStatus, MLJobType
from ml_service.models.model_version import ModelPurpose, ModelVersion
from ml_service.models.student_index import IndexCategory, StudentIndex
from ml_service.services.student_index_service import StudentIndexService

T0 = datetime(2026, 11, 1, 12, 0)


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    session.add(ModelVersion(
        id=1, version_label="v1", algorithm="XGBRegressor", purpose=ModelPurpose.index_regression,
        trained_at=T0, training_data_from=date(2023, 9, 1), training_data_to=date(2026, 6, 20),
        metrics={}, is_active=True, model_file_path="x.pkl",
    ))
    session.commit()
    yield session
    session.close()


def inference_job(db, status: MLJobStatus, hours: int, *scores: tuple[int, float]) -> MLJob:
    job = MLJob(
        job_type=MLJobType.inference,
        status=status,
        created_at=T0 + timedelta(hours=hours),
        started_at=T0 + timedelta(hours=hours),
        finished_at=T0 + timedelta(hours=hours, minutes=5) if status is not MLJobStatus.running else None,
    )
    db.add(job)
    db.flush()
    for student_id, value in scores:
        db.add(StudentIndex(
            student_id=student_id, semester_id=6, inference_job_id=job.id, model_version_id=1,
            index_value=value, category=IndexCategory.high, calculated_at=T0 + timedelta(hours=hours, minutes=1),
        ))
    db.commit()
    return job


def test_current_index_comes_from_the_latest_succeeded_run(db):
    inference_job(db, MLJobStatus.succeeded, 0, (1, 70.0), (2, 60.0))
    latest = inference_job(db, MLJobStatus.succeeded, 1, (1, 75.0), (2, 65.0))

    current = StudentIndexService(db).get_current_for_student(1)

    assert current.index_value == 75.0
    assert current.inference_job_id == latest.id


def test_a_run_in_progress_is_not_visible_yet(db):
    inference_job(db, MLJobStatus.succeeded, 0, (1, 70.0), (2, 60.0))
    inference_job(db, MLJobStatus.running, 1, (1, 10.0))

    assert StudentIndexService(db).get_current_for_student(1).index_value == 70.0
    assert StudentIndexService(db).get_current_for_student(2).index_value == 60.0


def test_a_failed_run_is_ignored_even_where_it_wrote_rows(db):
    inference_job(db, MLJobStatus.succeeded, 0, (1, 70.0))
    inference_job(db, MLJobStatus.failed, 1, (1, 10.0))

    assert StudentIndexService(db).get_current_for_student(1).index_value == 70.0
    assert [i.index_value for i in StudentIndexService(db).get_history_for_student(1)] == [70.0]


def test_a_student_missing_from_the_latest_run_has_no_current_index(db):
    inference_job(db, MLJobStatus.succeeded, 0, (1, 70.0), (2, 60.0))
    inference_job(db, MLJobStatus.succeeded, 1, (1, 75.0))

    assert StudentIndexService(db).get_current_for_student(2) is None
    assert [i.index_value for i in StudentIndexService(db).get_history_for_student(2)] == [60.0]


def test_history_lists_succeeded_runs_oldest_first(db):
    inference_job(db, MLJobStatus.succeeded, 0, (1, 70.0))
    inference_job(db, MLJobStatus.succeeded, 1, (1, 75.0))
    inference_job(db, MLJobStatus.running, 2, (1, 1.0))

    assert [i.index_value for i in StudentIndexService(db).get_history_for_student(1)] == [70.0, 75.0]


def test_nothing_is_current_before_the_first_run_finishes(db):
    inference_job(db, MLJobStatus.running, 0, (1, 70.0))

    assert StudentIndexService(db).get_current_for_student(1) is None
    assert StudentIndexService(db).get_current_for_student_full(1) is None


@pytest.fixture()
def client(db):
    app = FastAPI()
    app.include_router(student_indexes.router)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_latest_endpoints_serve_the_current_run_with_its_job_id(client, db):
    inference_job(db, MLJobStatus.succeeded, 0, (1, 70.0), (2, 60.0))
    latest = inference_job(db, MLJobStatus.succeeded, 1, (1, 75.0))

    response = client.get("/student-indexes/1/latest")
    full = client.get("/student-indexes/1/latest/full")

    assert response.json()["index_value"] == 75.0
    assert response.json()["inference_job_id"] == latest.id
    assert full.json()["inference_job_id"] == latest.id


def test_latest_is_404_for_a_student_not_in_the_current_run(client, db):
    inference_job(db, MLJobStatus.succeeded, 0, (1, 70.0), (2, 60.0))
    inference_job(db, MLJobStatus.succeeded, 1, (1, 75.0))

    response = client.get("/student-indexes/2/latest")

    assert response.status_code == 404
    assert response.json()["detail"] == "No index for this student in the latest completed inference run"
    assert len(client.get("/student-indexes/2/history").json()) == 1
