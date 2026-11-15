import logging

from ml_service.clients.import_service_client import ImportServiceClient
from ml_service.clients.insights_service_client import InsightsServiceClient
from ml_service.ml.inference.insights_payload import InsightsPayloadBuilder

logger = logging.getLogger(__name__)


def deliver_to_insights(
    payload: InsightsPayloadBuilder,
    inference_job_id: int,
    import_client: ImportServiceClient,
    insights_client: InsightsServiceClient | None,
) -> dict:
    if insights_client is None:
        return {"delivered": False, "reason": "INSIGHTS_SERVICE_URL is not set"}
    if not len(payload):
        return {"delivered": False, "reason": "no students were scored"}

    try:
        run = insights_client.submit_run(payload.build(inference_job_id, import_client.get_student_groups()))
    except Exception as e:
        logger.exception("Delivering inference job %s to insights-service failed", inference_job_id)
        return {"delivered": False, "reason": f"{type(e).__name__}: {e}"}

    return {"delivered": True, "insight_run_id": run["id"]}
