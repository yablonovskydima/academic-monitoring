from datetime import datetime

from ml_service.ml.targets.target_calculator import TargetCalculator
from ml_service.ml.encoding.feature_encoder import FeatureEncoder
from ml_service.ml.training.index_trainer import IndexTrainer
from ml_service.ml.persistence.model_persistence import ModelPersistence
from ml_service.services.model_version_service import ModelVersionService
from ml_service.schemas.model_version import ModelVersionCreate
from ml_service.models.model_version import ModelVersion, ModelPurpose

FORECAST_CONFIGS = [
    (2, ModelPurpose.index_forecast_horizon_2),
    (3, ModelPurpose.index_forecast_horizon_3),
]


class ForecastTrainingPipeline:
    def __init__(
        self,
        target_calculator: TargetCalculator,
        feature_encoder: FeatureEncoder,
        model_trainer: IndexTrainer,
        model_persistence: ModelPersistence,
        model_version_service: ModelVersionService,
    ):
        self.target_calculator = target_calculator
        self.feature_encoder = feature_encoder
        self.model_trainer = model_trainer
        self.model_persistence = model_persistence
        self.model_version_service = model_version_service

    def train_all(
        self,
        semester_features,
        all_semester_ids_ordered,
        version_label: str,
        training_data_from,
        training_data_to,
    ) -> dict[str, ModelVersion]:
        results: dict[str, ModelVersion] = {}

        for horizon, purpose in FORECAST_CONFIGS:
            X_raw, y = self.target_calculator.build_horizon_dataset(
                semester_features, all_semester_ids_ordered, horizon
            )

            if not X_raw:
                print(f"Skipping {purpose.value} — not enough historical data for horizon {horizon}")
                continue

            X_encoded = self.feature_encoder.encode(X_raw)
            result = self.model_trainer.train(X_encoded, y)
            model_file_path = self.model_persistence.save(result.model, f"{purpose.value}_{version_label}")

            results[purpose.value] = self.model_version_service.create(
                ModelVersionCreate(
                    version_label=version_label,
                    algorithm="XGBRegressor",
                    purpose=purpose,
                    trained_at=datetime.utcnow(),
                    training_data_from=training_data_from,
                    training_data_to=training_data_to,
                    metrics=result.metrics,
                    model_file_path=model_file_path,
                    is_active=True,
                )
            )

        return results