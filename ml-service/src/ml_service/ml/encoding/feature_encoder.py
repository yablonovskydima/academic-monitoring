import pandas as pd

from ml_service.schemas.student_semester_features import StudentSemesterFeatures
from ml_service.schemas.student_features import StudentFeaturesRaw

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
]


class FeatureEncoder:

    def encode(self, features_list: list[StudentSemesterFeatures | StudentFeaturesRaw]) -> pd.DataFrame:
        rows = [self._encode_one(f) for f in features_list]
        return pd.DataFrame(rows, columns=FEATURE_COLUMNS)

    def _encode_one(self, f: StudentSemesterFeatures | StudentFeaturesRaw) -> dict:
        avg_grade = f.avg_grade_overall if isinstance(f, StudentFeaturesRaw) else f.avg_grade

        return {
            "avg_grade": avg_grade,
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
        }