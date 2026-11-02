from sqlalchemy.orm import Session

from ml_service.models.risk_explanation import RiskExplanation
from ml_service.repositories.risk_explanation_repository import RiskExplanationRepository
from ml_service.schemas.risk_explanation import RiskExplanationCreate


class RiskExplanationService:
    def __init__(self, db: Session):
        self.repo = RiskExplanationRepository(db)

    def get_by_risk_assessment(self, risk_assessment_id: int) -> list[RiskExplanation]:
        return self.repo.get_by_risk_assessment(risk_assessment_id)

    def bulk_create_many(
        self, items: list[tuple[int, RiskExplanationCreate]]
    ) -> list[RiskExplanation]:
        explanations = [
            RiskExplanation(risk_assessment_id=risk_assessment_id, **data.model_dump())
            for risk_assessment_id, data in items
        ]
        return self.repo.bulk_save(explanations)
