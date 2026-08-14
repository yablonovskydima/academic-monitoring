from ml_service.ml.encoding.feature_encoder import FeatureEncoder
from ml_service.ml.persistence.model_persistence import ModelPersistence
from ml_service.services.model_version_service import ModelVersionService
from ml_service.services.risk_assessment_service import RiskAssessmentService
from ml_service.schemas.risk_assessment import RiskAssessmentCreate
from ml_service.models.model_version import ModelPurpose
from ml_service.models.risk_assessment import RiskType

RISK_TYPE_BY_PURPOSE = {
    ModelPurpose.expulsion_classifier: RiskType.expulsion,
    ModelPurpose.debt_classifier: RiskType.academic_debt,
    ModelPurpose.admission_classifier: RiskType.exam_admission_denial,
}


class RiskInferencePipeline:
    def __init__(
        self,
        feature_encoder: FeatureEncoder,
        model_persistence: ModelPersistence,
        model_version_service: ModelVersionService,
        risk_assessment_service: RiskAssessmentService,
    ):
        self.feature_encoder = feature_encoder
        self.model_persistence = model_persistence
        self.model_version_service = model_version_service
        self.risk_assessment_service = risk_assessment_service

        self._versions: dict = {}
        self._models: dict = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        for purpose in RISK_TYPE_BY_PURPOSE:
            version = self.model_version_service.get_active_by_purpose(purpose)
            if version is None:
                raise ValueError(f"No active {purpose.value} model found. Train a model first.")
            self._versions[purpose] = version
            self._models[purpose] = self.model_persistence.load(version.model_file_path)

        self._loaded = True

    def process_batch(self, batch, student_indexes) -> None:
        self._ensure_loaded()

        X_encoded = self.feature_encoder.encode(batch)

        probabilities = {
            purpose: model.predict_proba(X_encoded)[:, 1]
            for purpose, model in self._models.items()
        }

        for idx, student_index in enumerate(student_indexes):
            assessments_data = [
                RiskAssessmentCreate(
                    risk_type=RISK_TYPE_BY_PURPOSE[purpose],
                    probability=float(proba_array[idx]),
                    model_version_id=self._versions[purpose].id,
                )
                for purpose, proba_array in probabilities.items()
            ]
            self.risk_assessment_service.bulk_create(student_index.id, assessments_data)