import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Float, Enum as SAEnum, BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ml_service.database import Base

if TYPE_CHECKING:
    from ml_service.models.model_version import ModelVersion
    from ml_service.models.index_explanation import IndexExplanation
    from ml_service.models.feature_snapshot import FeatureSnapshot
    from ml_service.models.risk_assessment import RiskAssessment
    from ml_service.models.index_forecast import IndexForecast


class IndexCategory(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class StudentIndex(Base):
    __tablename__ = "student_indexes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    student_id: Mapped[int] = mapped_column(Integer, index=True)
    semester_id: Mapped[int] = mapped_column(Integer, index=True)

    model_version_id: Mapped[int] = mapped_column(ForeignKey("model_versions.id"), index=True)
    index_value: Mapped[float] = mapped_column(Float)
    category: Mapped[IndexCategory] = mapped_column(SAEnum(IndexCategory, name="index_category_enum"))
    calculated_at: Mapped[datetime]

    model_version: Mapped["ModelVersion"] = relationship(back_populates="student_indexes")
    explanations: Mapped[list["IndexExplanation"]] = relationship(back_populates="student_index")
    feature_snapshot: Mapped["FeatureSnapshot"] = relationship(back_populates="student_index", uselist=False)
    risk_assessments: Mapped[list["RiskAssessment"]] = relationship(back_populates="student_index")
    forecasts: Mapped[list["IndexForecast"]] = relationship(back_populates="student_index")