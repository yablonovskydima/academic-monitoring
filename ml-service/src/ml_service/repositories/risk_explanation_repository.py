from sqlalchemy import select
from sqlalchemy.orm import Session

from ml_service.models.risk_explanation import RiskExplanation


class RiskExplanationRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_risk_assessment(self, risk_assessment_id: int) -> list[RiskExplanation]:
        return list(self.session.scalars(
            select(RiskExplanation)
            .where(RiskExplanation.risk_assessment_id == risk_assessment_id)
            .order_by(RiskExplanation.rank)
        ).all())

    def bulk_save(self, explanations: list[RiskExplanation]) -> list[RiskExplanation]:
        self.session.add_all(explanations)
        self.session.flush()
        self.session.commit()
        return explanations
