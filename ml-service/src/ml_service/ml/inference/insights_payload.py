from ml_service.models.student_index import StudentIndex
from ml_service.schemas.student_semester_features import StudentSemesterFeatures


class InsightsPayloadBuilder:
    def __init__(self):
        self._students: dict[int, dict] = {}

    def __len__(self) -> int:
        return len(self._students)

    def add_index(
        self, features: StudentSemesterFeatures, student_index: StudentIndex, contributions: list[dict],
    ) -> None:
        self._students[features.student_id] = {
            "student_id": features.student_id,
            "semester_id": features.semester_id,
            "student_index_id": student_index.id,
            "index_value": float(student_index.index_value),
            "index_category": student_index.category.value,
            "features": features.model_dump(mode="json"),
            "index_contributions": contributions,
            "risks": [],
            "forecasts": [],
        }

    def add_risk(self, student_id: int, risk_type: str, probability: float, contributions: list[dict]) -> None:
        self._students[student_id]["risks"].append({
            "risk_type": risk_type,
            "probability": float(probability),
            "contributions": contributions,
        })

    def add_forecast(self, student_id: int, semesters_ahead: int, predicted_index_value: float) -> None:
        self._students[student_id]["forecasts"].append({
            "semesters_ahead": semesters_ahead,
            "predicted_index_value": float(predicted_index_value),
        })

    def build(self, inference_job_id: int, group_by_student: dict[int, int]) -> dict:
        missing = sorted(student_id for student_id in self._students if student_id not in group_by_student)
        if missing:
            raise ValueError(f"import-service has no group for {len(missing)} scored students, e.g. {missing[:5]}")

        return {
            "source_job_id": inference_job_id,
            "predictions": [
                {**student, "group_id": group_by_student[student_id]}
                for student_id, student in self._students.items()
            ],
        }
