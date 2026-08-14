from sqlalchemy.orm import Session

from ml_service.models.model_version import ModelVersion, ModelPurpose
from ml_service.repositories.model_version_repository import ModelVersionRepository
from ml_service.schemas.model_version import ModelVersionCreate, ModelVersionUpdate


class ModelVersionService:
    def __init__(self, db: Session):
        self.repo = ModelVersionRepository(db)

    def get_by_id(self, version_id: int) -> ModelVersion | None:
        return self.repo.get_by_id(version_id)

    def get_active_by_purpose(self, purpose: ModelPurpose) -> ModelVersion | None:
        return self.repo.get_active_by_purpose(purpose)

    def get_all(self) -> list[ModelVersion]:
        return self.repo.get_all()

    def get_all_by_purpose(self, purpose: ModelPurpose) -> list[ModelVersion]:
        return self.repo.get_all_by_purpose(purpose)

    def create(self, data: ModelVersionCreate) -> ModelVersion:
        if data.is_active:
            self.repo.deactivate_all_by_purpose(data.purpose)

        version = ModelVersion(**data.model_dump())
        return self.repo.save(version)

    def update(self, version_id: int, data: ModelVersionUpdate) -> ModelVersion | None:
        version = self.repo.get_by_id(version_id)
        if version is None:
            return None

        update_fields = data.model_dump(exclude_unset=True)

        if update_fields.get("is_active") is True:
            self.repo.deactivate_all_by_purpose(version.purpose)

        for key, value in update_fields.items():
            setattr(version, key, value)

        return self.repo.save(version)

    def delete(self, version_id: int) -> bool:
        return self.repo.delete(version_id)