from datetime import datetime

from sqlalchemy.orm import Session
import shap

from ml_service.clients.import_service_client import ImportServiceClient
from ml_service.ml.feature_encoder import FeatureEncoder
from ml_service.ml.model_persistence import ModelPersistence
from ml_service.services.model_version_service import ModelVersionService
from ml_service.services.student_index_service import StudentIndexService
from ml_service.services.index_explanation_service import IndexExplanationService
from ml_service.services.feature_snapshot_service import FeatureSnapshotService
from ml_service.schemas.student_index import StudentIndexCreate
from ml_service.schemas.index_explanation import IndexExplanationCreate
from ml_service.schemas.feature_snapshot import FeatureSnapshotCreate
from ml_service.models.student_index import IndexCategory

BATCH_SIZE = 500
TOP_N_EXPLANATIONS = 5

CATEGORY_HIGH_THRESHOLD = 70.0
CATEGORY_MEDIUM_THRESHOLD = 40.0


class InferenceService:
    def __init__(self, db: Session):
        self.db = db
        self.import_client = ImportServiceClient()
        self.feature_encoder = FeatureEncoder()
        self.model_persistence = ModelPersistence()
        self.model_version_service = ModelVersionService(db)
        self.student_index_service = StudentIndexService(db)
        self.explanation_service = IndexExplanationService(db)
        self.snapshot_service = FeatureSnapshotService(db)

    def calculate_all_indexes(self) -> int:
        active_version = self.model_version_service.get_active()
        if active_version is None:
            raise ValueError("No active model version found. Train a model first.")

        model = self.model_persistence.load(active_version.model_file_path)
        explainer = shap.TreeExplainer(model)

        current_semester = self.import_client.get_current_semester()
        semester_id = current_semester["id"]

        all_features = self.import_client.get_current_features()

        processed_count = 0
        for i in range(0, len(all_features), BATCH_SIZE):
            batch = all_features[i:i + BATCH_SIZE]
            self._process_batch(batch, model, explainer, active_version.id, semester_id)
            processed_count += len(batch)
            print(f"  processed {processed_count}/{len(all_features)}")

        return processed_count

    def _process_batch(self, batch, model, explainer, model_version_id: int, semester_id: int) -> None:
        X_encoded = self.feature_encoder.encode(batch)
        predictions = model.predict(X_encoded)
        shap_values = explainer.shap_values(X_encoded)

        for idx, features in enumerate(batch):
            index_value = float(predictions[idx])
            category = self._determine_category(index_value)

            student_index = self.student_index_service.create(
                StudentIndexCreate(
                    student_id=features.student_id,
                    semester_id=semester_id,
                    model_version_id=model_version_id,
                    index_value=index_value,
                    category=category,
                    calculated_at=datetime.now(),
                )
            )

            self._save_explanations(student_index.id, X_encoded.iloc[idx], shap_values[idx])
            self._save_snapshot(student_index.id, features)

    def _determine_category(self, index_value: float) -> IndexCategory:
        if index_value >= CATEGORY_HIGH_THRESHOLD:
            return IndexCategory.high
        elif index_value >= CATEGORY_MEDIUM_THRESHOLD:
            return IndexCategory.medium
        return IndexCategory.low

    def _save_explanations(self, student_index_id: int, feature_row, shap_row) -> None:
        feature_names = feature_row.index.tolist()
        feature_values = feature_row.values.tolist()

        contributions = list(zip(feature_names, feature_values, shap_row))
        contributions.sort(key=lambda x: abs(x[2]), reverse=True)
        top_contributions = contributions[:TOP_N_EXPLANATIONS]

        explanations_data = [
            IndexExplanationCreate(
                feature_name=name,
                feature_value=float(value),
                shap_value=float(shap_val),
                rank=rank + 1,
            )
            for rank, (name, value, shap_val) in enumerate(top_contributions)
        ]

        self.explanation_service.bulk_create(student_index_id, explanations_data)

    def _save_snapshot(self, student_index_id: int, features) -> None:
        self.snapshot_service.create(
            student_index_id,
            FeatureSnapshotCreate(raw_features=features.model_dump()),
        )