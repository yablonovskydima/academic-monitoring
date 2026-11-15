from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from insights_service.database import Base, BigIntegerPK
from insights_service.models.enums import Theme

if TYPE_CHECKING:
    from insights_service.models.insight_run import InsightRun


class GroupSummary(Base):
    __tablename__ = "group_summaries"
    __table_args__ = (
        UniqueConstraint("run_id", "group_id", name="uq_group_summary_run_group"),
    )

    id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("insight_runs.id"), index=True)
    group_id: Mapped[int] = mapped_column(Integer, index=True)
    students_count: Mapped[int] = mapped_column(Integer)
    index_high_count: Mapped[int] = mapped_column(Integer)
    index_medium_count: Mapped[int] = mapped_column(Integer)
    index_low_count: Mapped[int] = mapped_column(Integer)
    expulsion_high_count: Mapped[int] = mapped_column(Integer)
    debt_high_count: Mapped[int] = mapped_column(Integer)
    admission_denied_count: Mapped[int] = mapped_column(Integer)
    attention_count: Mapped[int] = mapped_column(Integer)
    worsened_count: Mapped[int] = mapped_column(Integer)
    top_theme: Mapped[Theme | None] = mapped_column(SAEnum(Theme, name="insight_theme_enum"), nullable=True)

    run: Mapped["InsightRun"] = relationship(back_populates="group_summaries")
