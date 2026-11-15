from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from insights_service.database import Base, BigIntegerPK
from insights_service.models.enums import ChangeDirection, ChangeKind, RiskType

if TYPE_CHECKING:
    from insights_service.models.insight_run import InsightRun


class InsightChange(Base):
    __tablename__ = "insight_changes"

    id: Mapped[int] = mapped_column(BigIntegerPK, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("insight_runs.id"), index=True)
    previous_run_id: Mapped[int] = mapped_column(ForeignKey("insight_runs.id"))
    student_id: Mapped[int] = mapped_column(Integer, index=True)
    group_id: Mapped[int] = mapped_column(Integer, index=True)
    kind: Mapped[ChangeKind] = mapped_column(SAEnum(ChangeKind, name="insight_change_kind_enum"))
    risk_type: Mapped[RiskType | None] = mapped_column(
        SAEnum(RiskType, name="insight_risk_type_enum"), nullable=True,
    )
    from_value: Mapped[str] = mapped_column(String(20))
    to_value: Mapped[str] = mapped_column(String(20))
    direction: Mapped[ChangeDirection] = mapped_column(SAEnum(ChangeDirection, name="insight_change_direction_enum"))
    text: Mapped[str] = mapped_column(String(500))

    run: Mapped["InsightRun"] = relationship(back_populates="changes", foreign_keys=[run_id])
