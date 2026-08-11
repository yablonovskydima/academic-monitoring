from sqlalchemy import select
from sqlalchemy.orm import Session

from ml_service.models.risk_assessment import RiskAssessment, RiskType


class RiskAssessmentRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, assessment_id: int) -> RiskAssessment | None:
        return self.session.scalars(
            select(RiskAssessment).where(RiskAssessment.id == assessment_id)
        ).first()

    def get_by_student_index(self, student_index_id: int) -> list[RiskAssessment]:
        return list(self.session.scalars(
            select(RiskAssessment).where(RiskAssessment.student_index_id == student_index_id)
        ).all())

    def get_by_student_index_and_type(
        self, student_index_id: int, risk_type: RiskType
    ) -> RiskAssessment | None:
        return self.session.scalars(
            select(RiskAssessment).where(
                RiskAssessment.student_index_id == student_index_id,
                RiskAssessment.risk_type == risk_type,
            )
        ).first()

    def save(self, assessment: RiskAssessment) -> RiskAssessment:
        self.session.add(assessment)
        self.session.flush()
        self.session.commit()
        return assessment

    def bulk_save(self, assessments: list[RiskAssessment]) -> list[RiskAssessment]:
        self.session.add_all(assessments)
        self.session.flush()
        self.session.commit()
        return assessments

    def delete(self, assessment_id: int) -> bool:
        assessment = self.get_by_id(assessment_id)
        if assessment is None:
            return False
        self.session.delete(assessment)
        self.session.commit()
        return True