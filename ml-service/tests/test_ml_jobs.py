import threading
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ml_service.controllers import inference, training
from ml_service.controllers.jobs import get_job_service
from ml_service.models.ml_job import MLJob, MLJobStatus, MLJobType
from ml_service.services.ml_job_service import INTERRUPTED_ERROR, JobAlreadyActive, MLJobService, start_in_thread


@pytest.fixture()
def session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    MLJob.__table__.create(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def run_now(work):
    work()


def make_service(session_factory, training=None, inference=None, start=run_now):
    return MLJobService(
        session_factory=session_factory,
        runners={
            MLJobType.training: training or (lambda db: {"trained_models": {}}),
            MLJobType.inference: inference or (lambda db: {"processed": 3}),
        },
        start=start,
    )


def test_submit_returns_a_queued_job_and_the_job_then_succeeds(session_factory):
    service = make_service(session_factory)

    queued = service.submit(MLJobType.inference, requested_by=7)

    assert queued.status == MLJobStatus.queued
    assert queued.requested_by == 7
    done = service.get(MLJobType.inference, queued.id)
    assert done.status == MLJobStatus.succeeded
    assert done.result == {"processed": 3}
    assert done.started_at is not None and done.finished_at >= done.started_at
    assert done.error is None


def test_a_failing_runner_marks_the_job_failed_with_the_reason(session_factory):
    def broken(db):
        raise ValueError("No active index_regression model found. Train a model first.")

    service = make_service(session_factory, inference=broken)

    job = service.get(MLJobType.inference, service.submit(MLJobType.inference).id)

    assert job.status == MLJobStatus.failed
    assert job.error == "ValueError: No active index_regression model found. Train a model first."
    assert job.result is None


def test_a_second_job_of_the_same_type_is_refused_while_one_is_active(session_factory):
    service = make_service(session_factory, start=lambda work: None)
    first = service.submit(MLJobType.training)

    with pytest.raises(JobAlreadyActive) as refused:
        service.submit(MLJobType.training)

    assert refused.value.job.id == first.id


def test_training_and_inference_jobs_do_not_block_each_other(session_factory):
    service = make_service(session_factory, start=lambda work: None)

    service.submit(MLJobType.training)
    inference_job = service.submit(MLJobType.inference)

    assert inference_job.status == MLJobStatus.queued


def test_a_new_job_can_start_once_the_previous_one_finished(session_factory):
    service = make_service(session_factory)
    first = service.submit(MLJobType.training)

    second = service.submit(MLJobType.training)

    assert second.id != first.id
    assert service.latest(MLJobType.training).id == second.id


def test_jobs_left_active_by_a_restart_are_marked_failed(session_factory):
    stalled = make_service(session_factory, start=lambda work: None)
    job = stalled.submit(MLJobType.training)

    assert make_service(session_factory).fail_interrupted() == 1

    after = stalled.get(MLJobType.training, job.id)
    assert after.status == MLJobStatus.failed
    assert after.error == INTERRUPTED_ERROR
    assert make_service(session_factory).submit(MLJobType.training).status == MLJobStatus.queued


def test_the_database_itself_refuses_a_second_active_job_of_a_type(session_factory):
    from datetime import datetime

    from sqlalchemy.exc import IntegrityError

    with session_factory() as db:
        db.add(MLJob(job_type=MLJobType.training, status=MLJobStatus.running, created_at=datetime.now()))
        db.commit()
        db.add(MLJob(job_type=MLJobType.training, status=MLJobStatus.queued, created_at=datetime.now()))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        db.add(MLJob(job_type=MLJobType.training, status=MLJobStatus.failed, created_at=datetime.now()))
        db.add(MLJob(job_type=MLJobType.training, status=MLJobStatus.succeeded, created_at=datetime.now()))
        db.commit()


def test_get_does_not_return_a_job_of_the_other_type(session_factory):
    service = make_service(session_factory)
    job = service.submit(MLJobType.training)

    assert service.get(MLJobType.inference, job.id) is None
    assert service.get(MLJobType.training, 999) is None


def test_job_runs_in_the_background_and_is_visible_as_running(session_factory):
    release = threading.Event()
    started = threading.Event()

    def slow(db):
        started.set()
        release.wait(5)
        return {"trained_models": {"index_regression": {}}}

    service = make_service(session_factory, training=slow, start=start_in_thread)

    job = service.submit(MLJobType.training)

    assert started.wait(5)
    assert service.get(MLJobType.training, job.id).status == MLJobStatus.running
    with pytest.raises(JobAlreadyActive):
        service.submit(MLJobType.training)

    release.set()
    deadline = time.monotonic() + 5
    while service.get(MLJobType.training, job.id).status == MLJobStatus.running and time.monotonic() < deadline:
        time.sleep(0.01)
    assert service.get(MLJobType.training, job.id).status == MLJobStatus.succeeded


@pytest.fixture()
def client(session_factory):
    app = FastAPI()
    app.include_router(training.router)
    app.include_router(inference.router)
    holder = {"service": make_service(session_factory)}
    app.dependency_overrides[get_job_service] = lambda: holder["service"]
    return TestClient(app), holder


def test_post_returns_202_with_the_job(client):
    http, _ = client

    response = http.post("/training/jobs", json={"requested_by": 3})

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["job_type"] == "training"
    assert response.json()["requested_by"] == 3


def test_post_without_a_body_is_accepted(client):
    http, _ = client

    assert http.post("/inference/jobs").status_code == 202


def test_status_can_be_polled_by_id_and_as_latest(client):
    http, _ = client
    job_id = http.post("/inference/jobs").json()["id"]

    by_id = http.get(f"/inference/jobs/{job_id}")
    latest = http.get("/inference/jobs/latest")

    assert by_id.status_code == 200
    assert by_id.json()["status"] == "succeeded"
    assert by_id.json()["result"] == {"processed": 3}
    assert latest.json()["id"] == job_id


def test_post_while_active_is_409_and_points_to_the_running_job(client, session_factory):
    http, holder = client
    holder["service"] = make_service(session_factory, start=lambda work: None)
    first = http.post("/training/jobs").json()

    response = http.post("/training/jobs")

    assert response.status_code == 409
    assert response.json()["detail"]["job"]["id"] == first["id"]


def test_unknown_or_foreign_job_is_404(client):
    http, _ = client
    training_id = http.post("/training/jobs").json()["id"]

    assert http.get("/training/jobs/999").status_code == 404
    assert http.get(f"/inference/jobs/{training_id}").status_code == 404
    assert http.get("/inference/jobs/latest").status_code == 404


def test_the_old_synchronous_endpoints_are_gone(client):
    http, _ = client

    assert http.post("/training/train").status_code in (404, 405)
    assert http.post("/inference/predict-all").status_code in (404, 405)
