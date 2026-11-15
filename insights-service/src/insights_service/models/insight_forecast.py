from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from insights_service.database import Base, BigIntegerPK

if TYPE_CHECKING:
    from insights_service.models.student_insight import StudentInsight


class InsightForecast(Base):
    __tablename__ = "insight_forecasts"
    __table_args__ = (
        UniqueConstraint("student_insight_id", "semesters_ahead", name="uq_insight_forecast_student_horizon"),
    )

    id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    student_insight_id: Mapped[int] = mapped_column(ForeignKey("student_insights.id"), index=True)
    semesters_ahead: Mapped[int] = mapped_column(Integer)
    predicted_index_value: Mapped[float] = mapped_column(Float)

    student_insight: Mapped["StudentInsight"] = relationship(back_populates="forecasts")
