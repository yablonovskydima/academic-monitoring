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
from ml_service.services.risk_assessment_service import RiskAssessmentService
from ml_service.schemas.student_index import StudentIndexCreate
from ml_service.schemas.index_explanation import IndexExplanationCreate
from ml_service.schemas.feature_snapshot import FeatureSnapshotCreate
from ml_service.schemas.risk_assessment import RiskAssessmentCreate
from ml_service.models.student_index import IndexCategory
from ml_service.models.model_version import ModelPurpose
from ml_service.models.risk_assessment import RiskType
from ml_service.models.model_version import ModelVersion, ModelPurpose

BATCH_SIZE = 500
TOP_N_EXPLANATIONS = 5

CATEGORY_HIGH_THRESHOLD = 70.0
CATEGORY_MEDIUM_THRESHOLD = 40.0

RISK_TYPE_BY_PURPOSE = {
    ModelPurpose.expulsion_classifier: RiskType.expulsion,
    ModelPurpose.debt_classifier: RiskType.academic_debt,
    ModelPurpose.admission_classifier: RiskType.exam_admission_denial,
}


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
        self.risk_assessment_service = RiskAssessmentService(db)

    def calculate_all_indexes(self) -> int:
        index_version = self.model_version_service.get_active_by_purpose(ModelPurpose.index_regression)
        if index_version is None:
            raise ValueError("No active index_regression model found. Train a model first.")

        classifier_versions: dict[ModelPurpose, "ModelVersion"] = {}
        for purpose in (
            ModelPurpose.expulsion_classifier,
            ModelPurpose.debt_classifier,
            ModelPurpose.admission_classifier,
        ):
            version = self.model_version_service.get_active_by_purpose(purpose)
            if version is None:
                raise ValueError(f"No active {purpose.value} model found. Train a model first.")
            classifier_versions[purpose] = version

        index_model = self.model_persistence.load(index_version.model_file_path)
        classifier_models = {
            purpose: self.model_persistence.load(v.model_file_path)
            for purpose, v in classifier_versions.items()
        }

        explainer = shap.TreeExplainer(index_model)

        current_semester = self.import_client.get_current_semester()
        semester_id = current_semester["id"]

        all_features = self.import_client.get_current_features()

        processed_count = 0
        for i in range(0, len(all_features), BATCH_SIZE):
            batch = all_features[i:i + BATCH_SIZE]
            self._process_batch(
                batch, index_model, explainer, index_version.id,
                classifier_models, classifier_versions, semester_id,
            )
            processed_count += len(batch)
            print(f"  processed {processed_count}/{len(all_features)}")

        return processed_count

    def _process_batch(
        self, batch, index_model, explainer, index_version_id,
        classifier_models, classifier_versions, semester_id,
    ) -> None:
        X_encoded = self.feature_encoder.encode(batch)

        index_predictions = index_model.predict(X_encoded)
        shap_values = explainer.shap_values(X_encoded)

        risk_probabilities: dict[ModelPurpose, list[float]] = {}
        for purpose, model in classifier_models.items():
            proba = model.predict_proba(X_encoded)[:, 1]
            risk_probabilities[purpose] = proba

        for idx, features in enumerate(batch):
            index_value = float(index_predictions[idx])
            category = self._determine_category(index_value)

            student_index = self.student_index_service.create(
                StudentIndexCreate(
                    student_id=features.student_id,
                    semester_id=semester_id,
                    model_version_id=index_version_id,
                    index_value=index_value,
                    category=category,
                    calculated_at=datetime.utcnow(),
                )
            )

            self._save_explanations(student_index.id, X_encoded.iloc[idx], shap_values[idx])
            self._save_snapshot(student_index.id, features)
            self._save_risk_assessments(student_index.id, idx, risk_probabilities, classifier_versions)

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

    def _save_risk_assessments(
        self, student_index_id: int, idx: int,
        risk_probabilities: dict[ModelPurpose, list[float]],
        classifier_versions: dict[ModelPurpose, "ModelVersion"],
    ) -> None:
        assessments_data = [
            RiskAssessmentCreate(
                risk_type=RISK_TYPE_BY_PURPOSE[purpose],
                probability=float(proba_array[idx]),
                model_version_id=classifier_versions[purpose].id,
            )
            for purpose, proba_array in risk_probabilities.items()
        ]

        self.risk_assessment_service.bulk_create(student_index_id, assessments_data)