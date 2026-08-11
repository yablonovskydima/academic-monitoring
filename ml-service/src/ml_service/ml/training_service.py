from datetime import datetime

from ml_service.models.model_version import ModelVersion
from ml_service.schemas.model_version import ModelVersionCreate


def train_new_model(self, version_label: str) -> ModelVersion:
    semester_features = self.import_client.get_semester_features()

    if not semester_features:
        raise ValueError("No semester features received from import-service")

    all_semester_ids_ordered = sorted({f.semester_id for f in semester_features})

    X_raw, y = self.target_calculator.build_training_dataset(
        semester_features, all_semester_ids_ordered
    )

    if not X_raw:
        raise ValueError("No training data after target calculation")

    X_encoded = self.feature_encoder.encode(X_raw)
    result = self.model_trainer.train(X_encoded, y)
    model_file_path = self.model_persistence.save(result.model, version_label)

    semesters_used = self.import_client.get_semesters()
    relevant_semesters = [s for s in semesters_used if s["id"] in all_semester_ids_ordered]
    training_data_from = min(s["start_date"] for s in relevant_semesters)
    training_data_to = max(s["end_date"] for s in relevant_semesters)

    model_version = self.model_version_service.create(
        ModelVersionCreate(
            version_label=version_label,
            algorithm="XGBoost",
            trained_at=datetime.now(),
            training_data_from=training_data_from,
            training_data_to=training_data_to,
            metrics=result.metrics,
            model_file_path=model_file_path,
            is_active=True,
        )
    )

    return model_version