from ml_service.ml.encoding.feature_encoder import FeatureEncoder
from ml_service.ml.inference.shap_contributions import make_explainer, top_contributions
from ml_service.ml.persistence.model_persistence import ModelPersistence
from ml_service.services.model_version_service import ModelVersionService
from ml_service.services.risk_assessment_service import RiskAssessmentService
from ml_service.services.risk_explanation_service import RiskExplanationService
from ml_service.schemas.risk_assessment import RiskAssessmentCreate
from ml_service.schemas.risk_explanation import RiskExplanationCreate
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
        explanation_service: RiskExplanationService,
    ):
        self.feature_encoder = feature_encoder
        self.model_persistence = model_persistence
        self.model_version_service = model_version_service
        self.risk_assessment_service = risk_assessment_service
        self.explanation_service = explanation_service

        self._versions: dict = {}
        self._models: dict = {}
        self._explainers: dict = {}
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

    def set_background(self, background_rows) -> None:
        self._ensure_loaded()
        background = self.feature_encoder.encode(background_rows)
        self._explainers = {
            purpose: make_explainer(model, background[self.feature_encoder.columns_for(purpose)])
            for purpose, model in self._models.items()
        }

    def process_batch(self, batch, student_indexes) -> None:
        self._ensure_loaded()
        if not self._explainers:
            raise ValueError("set_background must be called before process_batch")

        X_encoded = self.feature_encoder.encode(batch)
        X_by_purpose = {
            purpose: X_encoded[self.feature_encoder.columns_for(purpose)]
            for purpose in self._models
        }

        probabilities = {
            purpose: model.predict_proba(X_by_purpose[purpose])[:, 1]
            for purpose, model in self._models.items()
        }
        shap_values = {
            purpose: explainer.shap_values(X_by_purpose[purpose])
            for purpose, explainer in self._explainers.items()
        }

        all_assessments: list[tuple[int, RiskAssessmentCreate]] = []
        assessment_sources: list[tuple[ModelPurpose, int]] = []

        for idx, student_index in enumerate(student_indexes):
            for purpose, proba_array in probabilities.items():
                all_assessments.append((
                    student_index.id,
                    RiskAssessmentCreate(
                        risk_type=RISK_TYPE_BY_PURPOSE[purpose],
                        probability=float(proba_array[idx]),
                        model_version_id=self._versions[purpose].id,
                    ),
                ))
                assessment_sources.append((purpose, idx))

        created_assessments = self.risk_assessment_service.bulk_create_many(all_assessments)

        all_explanations: list[tuple[int, RiskExplanationCreate]] = []

        for assessment, (purpose, idx) in zip(created_assessments, assessment_sources):
            for contribution in top_contributions(X_by_purpose[purpose].iloc[idx], shap_values[purpose][idx]):
                all_explanations.append((assessment.id, RiskExplanationCreate(**contribution)))

        self.explanation_service.bulk_create_many(all_explanations)
