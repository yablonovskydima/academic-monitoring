from sqlalchemy.orm import Session

from ml_service.clients.import_service_client import ImportServiceClient
from ml_service.ml.targets.target_calculator import TargetCalculator
from ml_service.ml.encoding.feature_encoder import FeatureEncoder
from ml_service.ml.training.index_trainer import IndexTrainer
from ml_service.ml.training.risk_trainer import RiskTrainer
from ml_service.ml.training.index_training_pipeline import IndexTrainingPipeline
from ml_service.ml.training.risk_training_pipeline import RiskTrainingPipeline
from ml_service.ml.training.forecast_training_pipeline import ForecastTrainingPipeline
from ml_service.ml.persistence.model_persistence import ModelPersistence
from ml_service.services.model_version_service import ModelVersionService
from ml_service.services.model_promotion_service import ModelPromotionService, PromotionResult


class TrainingService:
    def __init__(self, db: Session):
        self.import_client = ImportServiceClient()

        target_calculator = TargetCalculator()
        feature_encoder = FeatureEncoder()
        model_trainer = IndexTrainer()
        classifier_trainer = RiskTrainer()
        model_persistence = ModelPersistence()
        model_version_service = ModelVersionService(db)
        promotion_service = ModelPromotionService(model_version_service, model_persistence)

        self.index_pipeline = IndexTrainingPipeline(
            target_calculator, feature_encoder, model_trainer, model_persistence, promotion_service
        )
        self.risk_pipeline = RiskTrainingPipeline(
            target_calculator, feature_encoder, classifier_trainer, model_persistence, promotion_service
        )
        self.forecast_pipeline = ForecastTrainingPipeline(
            target_calculator, feature_encoder, model_trainer, model_persistence, promotion_service
        )

    def train_all_models(self) -> dict[str, PromotionResult]:
        semester_features = self.import_client.get_semester_features()
        if not semester_features:
            raise ValueError("No semester features received from import-service")

        all_semester_ids_ordered = sorted({f.semester_id for f in semester_features})

        semesters = self.import_client.get_semesters()
        relevant_semesters = [s for s in semesters if s["id"] in all_semester_ids_ordered]
        training_data_from = min(s["start_date"] for s in relevant_semesters)
        training_data_to = max(s["end_date"] for s in relevant_semesters)

        results: dict[str, PromotionResult] = {}

        results["index_regression"] = self.index_pipeline.train(
            semester_features, all_semester_ids_ordered,
            training_data_from, training_data_to,
        )

        results.update(self.risk_pipeline.train_all(
            semester_features, all_semester_ids_ordered,
            training_data_from, training_data_to,
        ))

        results.update(self.forecast_pipeline.train_all(
            semester_features, all_semester_ids_ordered,
            training_data_from, training_data_to,
        ))

        return results
