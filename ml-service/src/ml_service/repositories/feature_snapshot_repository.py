from sqlalchemy import select
from sqlalchemy.orm import Session

from ml_service.models.feature_snapshot import FeatureSnapshot


class FeatureSnapshotRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, snapshot_id: int) -> FeatureSnapshot | None:
        return self.session.scalars(
            select(FeatureSnapshot).where(FeatureSnapshot.id == snapshot_id)
        ).first()

    def get_by_student_index(self, student_index_id: int) -> FeatureSnapshot | None:
        return self.session.scalars(
            select(FeatureSnapshot).where(FeatureSnapshot.student_index_id == student_index_id)
        ).first()

    def save(self, snapshot: FeatureSnapshot) -> FeatureSnapshot:
        self.session.add(snapshot)
        self.session.flush()
        self.session.commit()
        return snapshot

    def bulk_save(self, snapshots: list[FeatureSnapshot]) -> list[FeatureSnapshot]:
        self.session.add_all(snapshots)
        self.session.flush()
        self.session.commit()
        return snapshots

    def delete(self, snapshot_id: int) -> bool:
        snapshot = self.get_by_id(snapshot_id)
        if snapshot is None:
            return False
        self.session.delete(snapshot)
        self.session.commit()
        return True