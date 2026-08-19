from datetime import datetime

from ml_service.services.model_version_service import ModelVersionService
from ml_service.schemas.model_version import ModelVersionCreate
from ml_service.models.model_version import ModelVersion, ModelPurpose

RISK_CONFIGS = [
    # (purpose, label method name, requires_next_semester)
    (ModelPurpose.expulsion_classifier, "calculate_expulsion_label", False),
    # debt depends on repeated_subjects_count, which compares this
    # semester's subjects with the following semester's — a student's
    # last available semester must be excluded, otherwise it gets a
    # false repeated_subjects_count=0 (no next semester to compare to).
    (ModelPurpose.debt_classifier, "calculate_debt_label", True),
    (ModelPurpose.admission_classifier, "calculate_admission_denial_label", False),
]


class RiskTrainingPipeline:
    def __init__(
        self,
        target_calculator,
        feature_encoder,
        risk_trainer,
        model_persistence,
        model_version_service: ModelVersionService,
    ):
        self.target_calculator = target_calculator
        self.feature_encoder = feature_encoder
        self.risk_trainer = risk_trainer
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

        for purpose, label_method_name, requires_next_semester in RISK_CONFIGS:
            label_fn = getattr(self.target_calculator, label_method_name)

            X_raw, y = self.target_calculator.build_classification_dataset(
                semester_features, all_semester_ids_ordered, label_fn,
                requires_next_semester=requires_next_semester,
            )

            # --- ЛОГ: розподіл класів перед навчанням ---
            positive_count = sum(y)
            total_count = len(y)
            print(
                f"[risk_training] {purpose.value}: "
                f"total={total_count}, positive={positive_count}, "
                f"negative={total_count - positive_count}, "
                f"unique_classes={set(y)}"
            )

            if len(set(y)) < 2:
                print(f"[risk_training] SKIPPING {purpose.value} — only one class present, cannot train.")
                continue

            X_encoded = self.feature_encoder.encode(X_raw)
            result = self.risk_trainer.train(X_encoded, y)
            model_file_path = self.model_persistence.save(result.model, f"{purpose.value}_{version_label}")

            results[purpose.value] = self.model_version_service.create(
                ModelVersionCreate(
                    version_label=version_label,
                    algorithm="XGBClassifier",
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