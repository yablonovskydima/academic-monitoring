import pandas as pd

from ml_service.models.model_version import ModelPurpose
from ml_service.schemas.student_semester_features import StudentSemesterFeatures

FEATURE_COLUMNS = [
    "avg_grade",
    "grade_stddev",
    "lecture_absence_percent",
    "lab_absence_percent",
    "absence_percent",
    "unworked_absences_count",
    "missing_submissions_count",
    "late_submissions_count",
    "course_year",
    "study_mode_full_time",
    "study_mode_part_time",
    "study_mode_individual_schedule",
    "avg_grade_delta",
    "absence_percent_delta",
    "missing_submissions_delta",
    "cumulative_avg_grade",
    "cumulative_absence_percent",
    "cumulative_avg_missing_submissions",
    "cumulative_avg_late_submissions",
    "semesters_completed_count",
]

# admission_denial is a same-semester threshold rule computed directly
# from this semester's own absence/grade values. The cumulative_*
# columns are smoothed versions of those same values, so they add
# redundant correlation with the label instead of new information.
EXCLUDED_COLUMNS_BY_PURPOSE: dict[ModelPurpose, list[str]] = {
    ModelPurpose.admission_classifier: [
        "cumulative_avg_grade",
        "cumulative_absence_percent",
        "cumulative_avg_missing_submissions",
        "cumulative_avg_late_submissions",
    ],
}


class FeatureEncoder:

    def columns_for(self, purpose: ModelPurpose | None) -> list[str]:
        excluded = EXCLUDED_COLUMNS_BY_PURPOSE.get(purpose, [])
        return [c for c in FEATURE_COLUMNS if c not in excluded]

    def encode(
        self,
        features_list: list[StudentSemesterFeatures],
        purpose: ModelPurpose | None = None,
    ) -> pd.DataFrame:
        columns = self.columns_for(purpose)
        rows = [self._encode_one(f) for f in features_list]
        return pd.DataFrame(rows, columns=columns)

    def _encode_one(self, f: StudentSemesterFeatures) -> dict:
        return {
            "avg_grade": f.avg_grade,
            "grade_stddev": f.grade_stddev,
            "lecture_absence_percent": f.lecture_absence_percent,
            "lab_absence_percent": f.lab_absence_percent,
            "absence_percent": f.absence_percent,
            "unworked_absences_count": f.unworked_absences_count,
            "missing_submissions_count": f.missing_submissions_count,
            "late_submissions_count": f.late_submissions_count,
            "course_year": f.course_year,
            "study_mode_full_time": 1 if f.study_mode == "full_time" else 0,
            "study_mode_part_time": 1 if f.study_mode == "part_time" else 0,
            "study_mode_individual_schedule": 1 if f.study_mode == "individual_schedule" else 0,
            "avg_grade_delta": f.avg_grade_delta,
            "absence_percent_delta": f.absence_percent_delta,
            "missing_submissions_delta": f.missing_submissions_delta,
            "cumulative_avg_grade": f.cumulative_avg_grade,
            "cumulative_absence_percent": f.cumulative_absence_percent,
            "cumulative_avg_missing_submissions": f.cumulative_avg_missing_submissions,
            "cumulative_avg_late_submissions": f.cumulative_avg_late_submissions,
            "semesters_completed_count": f.semesters_completed_count,
        }
