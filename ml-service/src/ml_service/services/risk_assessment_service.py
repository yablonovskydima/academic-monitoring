from sqlalchemy.orm import Session

from ml_service.models.risk_assessment import RiskAssessment, RiskType
from ml_service.repositories.risk_assessment_repository import RiskAssessmentRepository
from ml_service.schemas.risk_assessment import RiskAssessmentCreate


class RiskAssessmentService:
    def __init__(self, db: Session):
        self.repo = RiskAssessmentRepository(db)

    def get_by_student_index(self, student_index_id: int) -> list[RiskAssessment]:
        return self.repo.get_by_student_index(student_index_id)

    def get_by_student_index_and_type(
        self, student_index_id: int, risk_type: RiskType
    ) -> RiskAssessment | None:
        return self.repo.get_by_student_index_and_type(student_index_id, risk_type)

    def create(self, student_index_id: int, data: RiskAssessmentCreate) -> RiskAssessment:
        assessment = RiskAssessment(student_index_id=student_index_id, **data.model_dump())
        return self.repo.save(assessment)

    def bulk_create(
        self, student_index_id: int, items_data: list[RiskAssessmentCreate]
    ) -> list[RiskAssessment]:
        assessments = [
            RiskAssessment(student_index_id=student_index_id, **data.model_dump())
            for data in items_data
        ]
        return self.repo.bulk_save(assessments)

    def bulk_create_many(
        self, items: list[tuple[int, RiskAssessmentCreate]]
    ) -> list[RiskAssessment]:
        assessments = [
            RiskAssessment(student_index_id=student_index_id, **data.model_dump())
            for student_index_id, data in items
        ]
        return self.repo.bulk_save(assessments)

    def delete(self, assessment_id: int) -> bool:
        return self.repo.delete(assessment_id)