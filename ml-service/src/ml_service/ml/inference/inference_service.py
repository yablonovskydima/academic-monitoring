import logging

from sqlalchemy.orm import Session

from ml_service.clients.import_service_client import ImportServiceClient
from ml_service.ml.encoding.feature_encoder import FeatureEncoder
from ml_service.ml.persistence.model_persistence import ModelPersistence
from ml_service.ml.inference.index_inference_pipeline import IndexInferencePipeline
from ml_service.ml.inference.risk_inference_pipeline import RiskInferencePipeline
from ml_service.ml.inference.forecast_inference_pipeline import ForecastInferencePipeline
from ml_service.services.model_version_service import ModelVersionService
from ml_service.services.student_index_service import StudentIndexService
from ml_service.services.index_explanation_service import IndexExplanationService
from ml_service.services.feature_snapshot_service import FeatureSnapshotService
from ml_service.services.risk_assessment_service import RiskAssessmentService
from ml_service.services.index_forecast_service import IndexForecastService

BATCH_SIZE = 500

logger = logging.getLogger(__name__)

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
            RiskAssessmentService(db),
        )
        self.forecast_pipeline = ForecastInferencePipeline(
            feature_encoder, model_persistence, model_version_service,
            IndexForecastService(db),
        )

    def calculate_all_indexes(self) -> int:
        semester_features = self.import_client.get_semester_features()
        if not semester_features:
            raise ValueError("No semester features received from import-service")

        latest_by_student = {}
        for features in semester_features:
            current = latest_by_student.get(features.student_id)
            if current is None or features.semester_id > current.semester_id:
                latest_by_student[features.student_id] = features

        all_features = list(latest_by_student.values())

        processed_count = 0

        for i in range(0, len(all_features), BATCH_SIZE):
            batch = all_features[i:i + BATCH_SIZE]

            student_indexes = self.index_pipeline.process_batch(batch)

            self.risk_pipeline.process_batch(batch, student_indexes)

            self.forecast_pipeline.process_batch(batch, student_indexes)

            processed_count += len(batch)

            logger.info("Processed %s/%s students", processed_count, len(all_features))

        return processed_count
