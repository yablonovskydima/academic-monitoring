from ml_service.controllers.jobs import make_job_router
from ml_service.models.ml_job import MLJobType

router = make_job_router("/inference", MLJobType.inference)
