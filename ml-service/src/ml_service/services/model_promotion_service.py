from dataclasses import dataclass
from datetime import date, datetime

from ml_service.config import KEEP_INACTIVE_MODEL_VERSIONS
from ml_service.ml.persistence.model_persistence import ModelPersistence
from ml_service.models.model_version import ModelPurpose, ModelVersion
from ml_service.schemas.model_version import ModelVersionCreate
from ml_service.services.model_version_service import ModelVersionService

METRIC_BY_PURPOSE: dict[ModelPurpose, str] = {
    ModelPurpose.index_regression: "r2",
    ModelPurpose.index_forecast_horizon_2: "r2",
    ModelPurpose.index_forecast_horizon_3: "r2",
    ModelPurpose.expulsion_classifier: "f1",
    ModelPurpose.debt_classifier: "f1",
    ModelPurpose.admission_classifier: "f1",
}


@dataclass
class PromotionResult:
    version: ModelVersion
    promoted: bool
    warning: str | None


class ModelPromotionService:
    def __init__(
        self,
        model_version_service: ModelVersionService,
        model_persistence: ModelPersistence,
    ):
        self.model_version_service = model_version_service
        self.model_persistence = model_persistence

    def next_version_label(self, purpose: ModelPurpose) -> str:
        existing = self.model_version_service.get_all_by_purpose(purpose)
        return f"v{len(existing) + 1}"

    def load_active_model(self, purpose: ModelPurpose):
        active = self.model_version_service.get_active_by_purpose(purpose)
        if active is None:
            return None
        return self.model_persistence.load(active.model_file_path)

    def register(
        self,
        purpose: ModelPurpose,
        version_label: str,
        algorithm: str,
        trained_at: datetime,
        training_data_from: date,
        training_data_to: date,
        metrics: dict,
        model_file_path: str,
    ) -> PromotionResult:
        active = self.model_version_service.get_active_by_purpose(purpose)
        promoted, warning = self._compare(purpose, metrics, active)

        version = self.model_version_service.create(
            ModelVersionCreate(
                version_label=version_label,
                algorithm=algorithm,
                purpose=purpose,
                trained_at=trained_at,
                training_data_from=training_data_from,
                training_data_to=training_data_to,
                metrics=metrics,
                model_file_path=model_file_path,
                is_active=promoted,
            )
        )

        self._cleanup_old_versions(purpose)

        return PromotionResult(version=version, promoted=promoted, warning=warning)

    def _compare(
        self,
        purpose: ModelPurpose,
        new_metrics: dict,
        active: ModelVersion | None,
    ) -> tuple[bool, str | None]:
        if active is None:
            return True, None

        metric_name = METRIC_BY_PURPOSE[purpose]
        new_value = new_metrics.get(metric_name)
        old_value = active.metrics.get(metric_name)

        if new_value is None or old_value is None or new_value > old_value:
            return True, None

        warning = (
            f"New version is not better than active {active.version_label} "
            f"({metric_name}: new={new_value:.4f} <= active={old_value:.4f}) - "
            f"keeping {active.version_label} active."
        )
        return False, warning

    def _cleanup_old_versions(self, purpose: ModelPurpose) -> None:
        versions = self.model_version_service.get_all_by_purpose(purpose)
        inactive = sorted(
            (v for v in versions if not v.is_active),
            key=lambda v: v.trained_at,
            reverse=True,
        )

        for stale in inactive[KEEP_INACTIVE_MODEL_VERSIONS:]:
            try:
                self.model_persistence.delete(stale.model_file_path)
                self.model_version_service.delete(stale.id)
            except Exception as e:
                self.model_version_service.repo.session.rollback()
                print(f"[model_promotion] could not remove stale version {stale.id}: {e}")
