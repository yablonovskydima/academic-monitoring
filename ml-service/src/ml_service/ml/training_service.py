from datetime import datetime

from sqlalchemy.orm import Session

from ml_service.clients.import_service_client import ImportServiceClient
from ml_service.ml.target_calculator import TargetCalculator
from ml_service.ml.feature_encoder import FeatureEncoder
from ml_service.ml.model_trainer import ModelTrainer
from ml_service.ml.classifier_trainer import ClassifierTrainer
from ml_service.ml.model_persistence import ModelPersistence
from ml_service.services.model_version_service import ModelVersionService
from ml_service.schemas.model_version import ModelVersionCreate
from ml_service.models.model_version import ModelVersion, ModelPurpose


class TrainingService:
    def __init__(self, db: Session):
        self.db = db
        self.import_client = ImportServiceClient()
        self.target_calculator = TargetCalculator()
        self.feature_encoder = FeatureEncoder()
        self.model_trainer = ModelTrainer()
        self.classifier_trainer = ClassifierTrainer()
        self.model_persistence = ModelPersistence()
        self.model_version_service = ModelVersionService(db)

    def train_all_models(self, version_label: str) -> dict[str, ModelVersion]:
        semester_features = self.import_client.get_semester_features()
        if not semester_features:
            raise ValueError("No semester features received from import-service")

        all_semester_ids_ordered = sorted({f.semester_id for f in semester_features})

        semesters = self.import_client.get_semesters()
        relevant_semesters = [s for s in semesters if s["id"] in all_semester_ids_ordered]
        training_data_from = min(s["start_date"] for s in relevant_semesters)
        training_data_to = max(s["end_date"] for s in relevant_semesters)

        results: dict[str, ModelVersion] = {}

        results["index_regression"] = self._train_regression(
            semester_features, all_semester_ids_ordered, version_label,
            training_data_from, training_data_to,
        )

        classifier_configs = [
            ("expulsion_classifier", ModelPurpose.expulsion_classifier, self.target_calculator.calculate_expulsion_label),
            ("debt_classifier", ModelPurpose.debt_classifier, self.target_calculator.calculate_debt_label),
            ("admission_classifier", ModelPurpose.admission_classifier, self.target_calculator.calculate_admission_denial_label),
        ]

        for key, purpose, label_fn in classifier_configs:
            results[key] = self._train_classifier(
                semester_features, all_semester_ids_ordered, version_label,
                training_data_from, training_data_to, purpose, label_fn,
            )

        return results

    def _train_regression(
        self, semester_features, all_semester_ids_ordered, version_label,
        training_data_from, training_data_to,
    ) -> ModelVersion:
        X_raw, y = self.target_calculator.build_training_dataset(semester_features, all_semester_ids_ordered)
        X_encoded = self.feature_encoder.encode(X_raw)
        result = self.model_trainer.train(X_encoded, y)
        model_file_path = self.model_persistence.save(result.model, f"index_{version_label}")

        return self.model_version_service.create(
            ModelVersionCreate(
                version_label=version_label,
                algorithm="XGBRegressor",
                purpose=ModelPurpose.index_regression,
                trained_at=datetime.now(),
                training_data_from=training_data_from,
                training_data_to=training_data_to,
                metrics=result.metrics,
                model_file_path=model_file_path,
                is_active=True,
            )
        )

    def _train_classifier(
        self, semester_features, all_semester_ids_ordered, version_label,
        training_data_from, training_data_to, purpose, label_fn,
    ) -> ModelVersion:
        X_raw, y = self.target_calculator.build_classification_dataset(
            semester_features, all_semester_ids_ordered, label_fn
        )
        X_encoded = self.feature_encoder.encode(X_raw)
        result = self.classifier_trainer.train(X_encoded, y)
        model_file_path = self.model_persistence.save(result.model, f"{purpose.value}_{version_label}")

        return self.model_version_service.create(
            ModelVersionCreate(
                version_label=version_label,
                algorithm="XGBClassifier",
                purpose=purpose,
                trained_at=datetime.now(),
                training_data_from=training_data_from,
                training_data_to=training_data_to,
                metrics=result.metrics,
                model_file_path=model_file_path,
                is_active=True,
            )
        )