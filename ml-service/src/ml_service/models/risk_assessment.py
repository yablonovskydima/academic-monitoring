import enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Float, Enum as SAEnum, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ml_service.database import Base

if TYPE_CHECKING:
    from ml_service.models.student_index import StudentIndex
    from ml_service.models.model_version import ModelVersion


class RiskType(str, enum.Enum):
    expulsion = "expulsion"
    academic_debt = "academic_debt"
    exam_admission_denial = "exam_admission_denial"


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_index_id: Mapped[int] = mapped_column(ForeignKey("student_indexes.id"), index=True)
    model_version_id: Mapped[int] = mapped_column(ForeignKey("model_versions.id"), index=True)
    risk_type: Mapped[RiskType] = mapped_column(SAEnum(RiskType, name="risk_type_enum"))
    probability: Mapped[float] = mapped_column(Float)

    student_index: Mapped["StudentIndex"] = relationship(back_populates="risk_assessments")
    model_version: Mapped["ModelVersion"] = relationship()