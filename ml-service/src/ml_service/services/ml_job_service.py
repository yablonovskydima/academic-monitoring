import logging
import threading
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ml_service.database import SessionLocal
from ml_service.ml.inference.inference_service import InferenceService
from ml_service.ml.training.training_service import TrainingService
from ml_service.models.ml_job import MLJob, MLJobStatus, MLJobType
from ml_service.repositories.ml_job_repository import MLJobRepository
from ml_service.schemas.ml_job import MLJobOut

logger = logging.getLogger(__name__)

INTERRUPTED_ERROR = "Interrupted: ml-service stopped before the job finished"

Runner = Callable[[Session], dict]

_submit_lock = threading.Lock()


class JobAlreadyActive(Exception):
    def __init__(self, job: MLJobOut):
        super().__init__(f"A {job.job_type.value} job is already {job.status.value}")
        self.job = job


def run_training(db: Session) -> dict:
    results = TrainingService(db).train_all_models()
    return {
        "trained_models": {
            key: {
                "model_version_id": result.version.id,
                "version_label": result.version.version_label,
                "purpose": result.version.purpose.value,
                "metrics": result.version.metrics,
                "promoted": result.promoted,
                "warning": result.warning,
            }
            for key, result in results.items()
        },
    }


def run_inference(db: Session) -> dict:
    return {"processed": InferenceService(db).calculate_all_indexes()}


DEFAULT_RUNNERS: dict[MLJobType, Runner] = {
    MLJobType.training: run_training,
    MLJobType.inference: run_inference,
}


def start_in_thread(work: Callable[[], None]) -> None:
    threading.Thread(target=work, daemon=True, name="ml-job").start()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class MLJobService:
    def __init__(
        self,
        session_factory: Callable[[], Session] = SessionLocal,
        runners: dict[MLJobType, Runner] | None = None,
        start: Callable[[Callable[[], None]], None] = start_in_thread,
    ):
        self.session_factory = session_factory
        self.runners = runners or DEFAULT_RUNNERS
        self.start = start

    def submit(self, job_type: MLJobType, requested_by: int | None = None) -> MLJobOut:
        with _submit_lock, self.session_factory() as db:
            repo = MLJobRepository(db)

            active = repo.get_active_by_type(job_type)
            if active is not None:
                raise JobAlreadyActive(MLJobOut.model_validate(active))

            try:
                job = repo.save(MLJob(
                    job_type=job_type,
                    status=MLJobStatus.queued,
                    requested_by=requested_by,
                    created_at=_utc_now(),
                ))
            except IntegrityError:
                db.rollback()
                raise JobAlreadyActive(MLJobOut.model_validate(repo.get_active_by_type(job_type)))

            queued = MLJobOut.model_validate(job)

        self.start(lambda: self._execute(queued.id, job_type))
        return queued

    def get(self, job_type: MLJobType, job_id: int) -> MLJobOut | None:
        with self.session_factory() as db:
            job = MLJobRepository(db).get_by_id(job_id)
            if job is None or job.job_type != job_type:
                return None
            return MLJobOut.model_validate(job)

    def latest(self, job_type: MLJobType) -> MLJobOut | None:
        with self.session_factory() as db:
            job = MLJobRepository(db).get_latest_by_type(job_type)
            return MLJobOut.model_validate(job) if job is not None else None

    def fail_interrupted(self) -> int:
        with self.session_factory() as db:
            repo = MLJobRepository(db)
            interrupted = repo.get_all_active()
            for job in interrupted:
                job.status = MLJobStatus.failed
                job.finished_at = _utc_now()
                job.error = INTERRUPTED_ERROR
                repo.save(job)
            return len(interrupted)

    def _execute(self, job_id: int, job_type: MLJobType) -> None:
        self._update(job_id, status=MLJobStatus.running, started_at=_utc_now())

        try:
            with self.session_factory() as db:
                result = self.runners[job_type](db)
        except Exception as e:
            logger.exception("%s job %s failed", job_type.value, job_id)
            self._update(job_id, status=MLJobStatus.failed, finished_at=_utc_now(), error=f"{type(e).__name__}: {e}")
        else:
            self._update(job_id, status=MLJobStatus.succeeded, finished_at=_utc_now(), result=result)

    def _update(self, job_id: int, **changes) -> None:
        with self.session_factory() as db:
            repo = MLJobRepository(db)
            job = repo.get_by_id(job_id)
            for field, value in changes.items():
                setattr(job, field, value)
            repo.save(job)
