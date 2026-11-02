import logging

from sqlalchemy.orm import Session

from ml_service.clients.import_service_client import ImportServiceClient
from ml_service.ml.encoding.feature_encoder import FeatureEncoder
from ml_service.ml.persistence.model_persistence import ModelPersistence
from ml_service.ml.inference.index_inference_pipeline import IndexInferencePipeline
from ml_service.ml.inference.risk_inference_pipeline import RiskInferencePipeline
from ml_service.ml.inference.forecast_inference_pipeline import ForecastInferencePipeline
from ml_service.ml.inference.shap_contributions import background_sample
from ml_service.services.model_version_service import ModelVersionService
from ml_service.services.student_index_service import StudentIndexService
from ml_service.services.index_explanation_service import IndexExplanationService
from ml_service.services.feature_snapshot_service import FeatureSnapshotService
from ml_service.services.risk_assessment_service import RiskAssessmentService
from ml_service.services.risk_explanation_service import RiskExplanationService
from ml_service.services.index_forecast_service import IndexForecastService

BATCH_SIZE = 500

logger = logging.getLogger(__name__)


def current_semester_rows(semester_features: list) -> list:
    latest_semester_id = max(features.semester_id for features in semester_features)
    return [features for features in semester_features if features.semester_id == latest_semester_id]


class InferenceService:
    def __init__(self, db: Session):
        self.import_client = ImportServiceClient()
        feature_encoder = FeatureEncoder()
        model_persistence = ModelPersistence()
        model_version_service = ModelVersionService(db)

        self.index_pipeline = IndexInferencePipeline(
            feature_encoder, model_persistence, model_version_service,
            StudentIndexService(db), IndexExplanationService(db), FeatureSnapshotService(db),
        )
        self.risk_pipeline = RiskInferencePipeline(
            feature_encoder, model_persistence, model_version_service,
            RiskAssessmentService(db), RiskExplanationService(db),
        )
        self.forecast_pipeline = ForecastInferencePipeline(
            feature_encoder, model_persistence, model_version_service,
            IndexForecastService(db),
        )

    def calculate_all_indexes(self) -> int:
        semester_features = self.import_client.get_semester_features()
        if not semester_features:
            raise ValueError("No semester features received from import-service")

        all_features = current_semester_rows(semester_features)
        logger.info(
            "Scoring %s students enrolled in the latest semester, skipping %s who are no longer enrolled",
            len(all_features),
            len({f.student_id for f in semester_features}) - len(all_features),
        )

        background = background_sample(all_features)
        self.index_pipeline.set_background(background)
        self.risk_pipeline.set_background(background)

        processed_count = 0

        for i in range(0, len(all_features), BATCH_SIZE):
            batch = all_features[i:i + BATCH_SIZE]

            student_indexes = self.index_pipeline.process_batch(batch)

            self.risk_pipeline.process_batch(batch, student_indexes)

            self.forecast_pipeline.process_batch(batch, student_indexes)

            processed_count += len(batch)

            logger.info("Processed %s/%s students", processed_count, len(all_features))

        return processed_count
