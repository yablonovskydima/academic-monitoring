from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum as SAEnum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from insights_service.database import Base, BigIntegerPK
from insights_service.models.enums import IndexCategory

if TYPE_CHECKING:
    from insights_service.models.insight_forecast import InsightForecast
    from insights_service.models.insight_reason import InsightReason
    from insights_service.models.insight_run import InsightRun
    from insights_service.models.risk_insight import RiskInsight


class StudentInsight(Base):
    __tablename__ = "student_insights"
    __table_args__ = (
        UniqueConstraint("run_id", "student_id", name="uq_student_insight_run_student"),
    )

    id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("insight_runs.id"), index=True)
    student_id: Mapped[int] = mapped_column(Integer, index=True)
    group_id: Mapped[int] = mapped_column(Integer, index=True)
    semester_id: Mapped[int] = mapped_column(Integer)
    student_index_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    index_value: Mapped[float] = mapped_column(Float)
    index_category: Mapped[IndexCategory] = mapped_column(SAEnum(IndexCategory, name="insight_index_category_enum"))
    headline: Mapped[str] = mapped_column(String(500))

    run: Mapped["InsightRun"] = relationship(back_populates="student_insights")
    risks: Mapped[list["RiskInsight"]] = relationship(
        back_populates="student_insight", cascade="all, delete-orphan",
    )
    reasons: Mapped[list["InsightReason"]] = relationship(
        back_populates="student_insight", cascade="all, delete-orphan", order_by="InsightReason.rank",
    )
    forecasts: Mapped[list["InsightForecast"]] = relationship(
        back_populates="student_insight", cascade="all, delete-orphan", order_by="InsightForecast.semesters_ahead",
    )
