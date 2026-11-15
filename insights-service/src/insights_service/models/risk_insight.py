from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from insights_service.database import Base, BigIntegerPK
from insights_service.models.enums import RiskKind, RiskLevel, RiskType

if TYPE_CHECKING:
    from insights_service.models.student_insight import StudentInsight


class RiskInsight(Base):
    __tablename__ = "risk_insights"
    __table_args__ = (
        UniqueConstraint("student_insight_id", "risk_type", name="uq_risk_insight_student_type"),
    )

    id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    student_insight_id: Mapped[int] = mapped_column(ForeignKey("student_insights.id"), index=True)
    risk_type: Mapped[RiskType] = mapped_column(SAEnum(RiskType, name="insight_risk_type_enum"))
    kind: Mapped[RiskKind] = mapped_column(SAEnum(RiskKind, name="insight_risk_kind_enum"))
    level: Mapped[RiskLevel] = mapped_column(SAEnum(RiskLevel, name="insight_risk_level_enum"))
    probability: Mapped[float] = mapped_column(Float)

    student_insight: Mapped["StudentInsight"] = relationship(back_populates="risks")
