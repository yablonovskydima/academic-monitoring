from datetime import datetime

from ml_service.ml.targets.target_calculator import TargetCalculator
from ml_service.ml.encoding.feature_encoder import FeatureEncoder
from ml_service.ml.training.index_trainer import IndexTrainer
from ml_service.ml.persistence.model_persistence import ModelPersistence
from ml_service.services.model_promotion_service import ModelPromotionService, PromotionResult
from ml_service.models.model_version import ModelPurpose


class IndexTrainingPipeline:
    def __init__(
        self,
        target_calculator: TargetCalculator,
        feature_encoder: FeatureEncoder,
        model_trainer: IndexTrainer,
        model_persistence: ModelPersistence,
        promotion_service: ModelPromotionService,
    ):
        self.target_calculator = target_calculator
        self.feature_encoder = feature_encoder
        self.model_trainer = model_trainer
        self.model_persistence = model_persistence
        self.promotion_service = promotion_service

    def train(
        self,
        semester_features,
        all_semester_ids_ordered,
        training_data_from,
        training_data_to,
    ) -> PromotionResult:
        X_raw, y = self.target_calculator.build_horizon_dataset(
            semester_features, all_semester_ids_ordered, horizon=1
        )
        X_encoded = self.feature_encoder.encode(X_raw)
        result = self.model_trainer.train(X_encoded, y)

        version_label = self.promotion_service.next_version_label(ModelPurpose.index_regression)
        model_file_path = self.model_persistence.save(result.model, f"index_regression_{version_label}")

        return self.promotion_service.register(
            purpose=ModelPurpose.index_regression,
            version_label=version_label,
            algorithm="XGBRegressor",
            trained_at=datetime.now(),
            training_data_from=training_data_from,
            training_data_to=training_data_to,
            metrics=result.metrics,
            model_file_path=model_file_path,
        )
