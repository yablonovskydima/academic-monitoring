from pydantic import BaseModel


class StudentSemesterFeatures(BaseModel):
    student_id: int
    semester_id: int
    academic_year: str
    term: int
    course_year: int
    study_mode: str

    avg_grade: float
    grade_stddev: float

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

    disappeared_next_semester: bool
    repeated_subjects_count: int

    avg_grade_delta: float
    absence_percent_delta: float
    missing_submissions_delta: int

    cumulative_avg_grade: float
    cumulative_absence_percent: float
    cumulative_avg_missing_submissions: float
    cumulative_avg_late_submissions: float
    semesters_completed_count: int