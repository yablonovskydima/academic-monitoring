from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Float, Integer, String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ml_service.database import Base

if TYPE_CHECKING:
    from ml_service.models.student_index import StudentIndex


class IndexExplanation(Base):
    __tablename__ = "index_explanations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_index_id: Mapped[int] = mapped_column(ForeignKey("student_indexes.id"), index=True)
    feature_name: Mapped[str] = mapped_column(String(100))
    feature_value: Mapped[float] = mapped_column(Float)
    shap_value: Mapped[float] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer)

    student_index: Mapped["StudentIndex"] = relationship(back_populates="explanations")