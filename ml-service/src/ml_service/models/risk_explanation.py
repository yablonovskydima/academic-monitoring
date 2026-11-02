from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Float, Integer, String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ml_service.database import Base

if TYPE_CHECKING:
    from ml_service.models.risk_assessment import RiskAssessment


class RiskExplanation(Base):
    __tablename__ = "risk_explanations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    risk_assessment_id: Mapped[int] = mapped_column(ForeignKey("risk_assessments.id"), index=True)
    feature_name: Mapped[str] = mapped_column(String(100))
    feature_value: Mapped[float] = mapped_column(Float)
    shap_value: Mapped[float] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer)

    risk_assessment: Mapped["RiskAssessment"] = relationship(back_populates="explanations")
