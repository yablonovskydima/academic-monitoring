from datetime import datetime

import shap

from ml_service.ml.encoding.feature_encoder import FeatureEncoder
from ml_service.ml.persistence.model_persistence import ModelPersistence
from ml_service.services.model_version_service import ModelVersionService
from ml_service.services.student_index_service import StudentIndexService
from ml_service.services.index_explanation_service import IndexExplanationService
from ml_service.services.feature_snapshot_service import FeatureSnapshotService
from ml_service.schemas.student_index import StudentIndexCreate
from ml_service.schemas.index_explanation import IndexExplanationCreate
from ml_service.schemas.feature_snapshot import FeatureSnapshotCreate
from ml_service.models.model_version import ModelPurpose
from ml_service.models.student_index import IndexCategory, StudentIndex

TOP_N_EXPLANATIONS = 5
CATEGORY_HIGH_THRESHOLD = 70.0
CATEGORY_MEDIUM_THRESHOLD = 40.0


class IndexInferencePipeline:
    def __init__(
        self,
        feature_encoder: FeatureEncoder,
        model_persistence: ModelPersistence,
        model_version_service: ModelVersionService,
        student_index_service: StudentIndexService,
        explanation_service: IndexExplanationService,
        snapshot_service: FeatureSnapshotService,
    ):
        self.feature_encoder = feature_encoder
        self.model_persistence = model_persistence
        self.model_version_service = model_version_service
        self.student_index_service = student_index_service
        self.explanation_service = explanation_service
        self.snapshot_service = snapshot_service

        self._active_version = None
        self._model = None
        self._explainer = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return

        self._active_version = self.model_version_service.get_active_by_purpose(ModelPurpose.index_regression)
        if self._active_version is None:
            raise ValueError("No active index_regression model found. Train a model first.")

        self._model = self.model_persistence.load(self._active_version.model_file_path)
        self._explainer = shap.TreeExplainer(self._model)

    def process_batch(self, batch) -> list[StudentIndex]:
        self._ensure_loaded()

        X_encoded = self.feature_encoder.encode(batch, purpose=ModelPurpose.index_regression)
        predictions = self._model.predict(X_encoded)
        shap_values = self._explainer.shap_values(X_encoded)

        index_data_list = []
        for idx, features in enumerate(batch):
            index_value = float(predictions[idx])
            category = self._determine_category(index_value)

            index_data_list.append(StudentIndexCreate(
                student_id=features.student_id,
                semester_id=features.semester_id,
                model_version_id=self._active_version.id,
                index_value=index_value,
                category=category,
                calculated_at=datetime.utcnow(),
            ))

        created_indexes = self.student_index_service.bulk_create(index_data_list)

        all_explanations: list[tuple[int, IndexExplanationCreate]] = []
        all_snapshots: list[tuple[int, FeatureSnapshotCreate]] = []

        for idx, (student_index, features) in enumerate(zip(created_indexes, batch)):
            feature_row = X_encoded.iloc[idx]
            shap_row = shap_values[idx]

            for exp_data in self._build_explanations(feature_row, shap_row):
                all_explanations.append((student_index.id, exp_data))

            all_snapshots.append((
                student_index.id,
                FeatureSnapshotCreate(raw_features=features.model_dump()),
            ))

        self.explanation_service.bulk_create_many(all_explanations)
        self.snapshot_service.bulk_create_many(all_snapshots)

        return created_indexes

    def _determine_category(self, index_value: float) -> IndexCategory:
        if index_value >= CATEGORY_HIGH_THRESHOLD:
            return IndexCategory.high
        elif index_value >= CATEGORY_MEDIUM_THRESHOLD:
            return IndexCategory.medium
        return IndexCategory.low

    def _build_explanations(self, feature_row, shap_row) -> list[IndexExplanationCreate]:
        feature_names = feature_row.index.tolist()
        feature_values = feature_row.values.tolist()

        contributions = list(zip(feature_names, feature_values, shap_row))
        contributions.sort(key=lambda x: abs(x[2]), reverse=True)
        top_contributions = contributions[:TOP_N_EXPLANATIONS]

        return [
            IndexExplanationCreate(
                feature_name=name,
                feature_value=float(value),
                shap_value=float(shap_val),
                rank=rank + 1,
            )
            for rank, (name, value, shap_val) in enumerate(top_contributions)
        ]