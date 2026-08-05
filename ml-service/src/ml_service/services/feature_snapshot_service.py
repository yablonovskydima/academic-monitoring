from sqlalchemy.orm import Session

from ml_service.models.feature_snapshot import FeatureSnapshot
from ml_service.repositories.feature_snapshot_repository import FeatureSnapshotRepository
from ml_service.schemas.feature_snapshot import FeatureSnapshotCreate


class FeatureSnapshotService:
    def __init__(self, db: Session):
        self.repo = FeatureSnapshotRepository(db)

    def get_by_student_index(self, student_index_id: int) -> FeatureSnapshot | None:
        return self.repo.get_by_student_index(student_index_id)

    def create(self, student_index_id: int, data: FeatureSnapshotCreate) -> FeatureSnapshot:
        snapshot = FeatureSnapshot(student_index_id=student_index_id, **data.model_dump())
        return self.repo.save(snapshot)

    def delete(self, snapshot_id: int) -> bool:
        return self.repo.delete(snapshot_id)