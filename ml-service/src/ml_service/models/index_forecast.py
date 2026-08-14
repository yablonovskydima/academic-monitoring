from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Float, Integer, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ml_service.database import Base

if TYPE_CHECKING:
    from ml_service.models.student_index import StudentIndex
    from ml_service.models.model_version import ModelVersion


class IndexForecast(Base):
    __tablename__ = "index_forecasts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_index_id: Mapped[int] = mapped_column(ForeignKey("student_indexes.id"), index=True)
    model_version_id: Mapped[int] = mapped_column(ForeignKey("model_versions.id"), index=True)
    semesters_ahead: Mapped[int] = mapped_column(Integer)
    predicted_index_value: Mapped[float] = mapped_column(Float)

    student_index: Mapped["StudentIndex"] = relationship(back_populates="forecasts")
    model_version: Mapped["ModelVersion"] = relationship()