from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, JSON, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ml_service.database import Base

if TYPE_CHECKING:
    from ml_service.models.student_index import StudentIndex


class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_index_id: Mapped[int] = mapped_column(ForeignKey("student_indexes.id"), unique=True, index=True)
    raw_features: Mapped[dict] = mapped_column(JSON)

    student_index: Mapped["StudentIndex"] = relationship(back_populates="feature_snapshot")