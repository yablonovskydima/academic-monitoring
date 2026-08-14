from pydantic import BaseModel


class SemesterAvgGrade(BaseModel):
    semester_id: int
    academic_year: str
    term: int
    avg_grade: float


class StudentFeaturesRaw(BaseModel):
    student_id: int
    course_year: int
    study_mode: str

    avg_grade_overall: float
    grade_stddev: float
    grade_trend: list[SemesterAvgGrade]

    total_sessions: int
    absences_count: int
    absence_percent: float
    unworked_absences_count: int

    lecture_absence_percent: float
    lab_absence_percent: float

    total_gradable_sessions: int
    graded_sessions_count: int
    missing_submissions_count: int
    late_submissions_count: int