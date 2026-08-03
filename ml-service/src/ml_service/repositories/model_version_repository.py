from sqlalchemy import select
from sqlalchemy.orm import Session

from ml_service.models.model_version import ModelVersion


class ModelVersionRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, version_id: int) -> ModelVersion | None:
        return self.session.scalars(
            select(ModelVersion).where(ModelVersion.id == version_id)
        ).first()

    def get_active(self) -> ModelVersion | None:
        return self.session.scalars(
            select(ModelVersion).where(ModelVersion.is_active.is_(True))
        ).first()

    def get_all(self) -> list[ModelVersion]:
        return list(self.session.scalars(select(ModelVersion)).all())

    def save(self, model_version: ModelVersion) -> ModelVersion:
        self.session.add(model_version)
        self.session.flush()
        self.session.commit()
        return model_version

    def deactivate_all(self) -> None:
        versions = self.get_all()
        for v in versions:
            v.is_active = False
        self.session.commit()

    def delete(self, version_id: int) -> bool:
        version = self.get_by_id(version_id)
        if version is None:
            return False
        self.session.delete(version)
        self.session.commit()
        return True