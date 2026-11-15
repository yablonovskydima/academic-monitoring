from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from insights_service.database import Base, BigIntegerPK
from insights_service.models.enums import InsightTarget, ReasonDirection, ReasonStrength, Theme

if TYPE_CHECKING:
    from insights_service.models.student_insight import StudentInsight


class InsightReason(Base):
    __tablename__ = "insight_reasons"

    id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    student_insight_id: Mapped[int] = mapped_column(ForeignKey("student_insights.id"), index=True)
    target: Mapped[InsightTarget] = mapped_column(SAEnum(InsightTarget, name="insight_target_enum"))
    theme: Mapped[Theme] = mapped_column(SAEnum(Theme, name="insight_theme_enum"))
    title: Mapped[str] = mapped_column(String(100))
    direction: Mapped[ReasonDirection] = mapped_column(SAEnum(ReasonDirection, name="insight_reason_direction_enum"))
    strength: Mapped[ReasonStrength] = mapped_column(SAEnum(ReasonStrength, name="insight_reason_strength_enum"))
    text: Mapped[str] = mapped_column(String(500))
    action: Mapped[str | None] = mapped_column(String(500), nullable=True)
    feature_name: Mapped[str] = mapped_column(String(100))
    feature_value: Mapped[float] = mapped_column(Float)
    percentile: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rank: Mapped[int] = mapped_column(Integer)

    student_insight: Mapped["StudentInsight"] = relationship(back_populates="reasons")
