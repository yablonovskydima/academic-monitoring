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
from ml_service.services.risk_assessment_service import RiskAssessmentService
from ml_service.services.index_forecast_service import IndexForecastService

BATCH_SIZE = 500


class InferenceService:
    def __init__(self, db: Session):
        self.import_client = ImportServiceClient()
        feature_encoder = FeatureEncoder()
        model_persistence = ModelPersistence()
        model_version_service = ModelVersionService(db)

        self.index_pipeline = IndexInferencePipeline(
            feature_encoder, model_persistence, model_version_service,
            StudentIndexService(db), IndexExplanationService(db),
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
        current_semester = self.import_client.get_current_semester()
        if not current_semester or "id" not in current_semester:
            raise ValueError("Could not determine current semester from import-service")
        semester_id = current_semester["id"]

        all_features = self.import_client.get_current_features()

        processed_count = 0
        for i in range(0, len(all_features), BATCH_SIZE):
            batch = all_features[i:i + BATCH_SIZE]

            student_indexes = self.index_pipeline.process_batch(batch, semester_id)
            self.risk_pipeline.process_batch(batch, student_indexes)
            self.forecast_pipeline.process_batch(batch, student_indexes)

            processed_count += len(batch)
            print(f"  processed {processed_count}/{len(all_features)}")

        return processed_count