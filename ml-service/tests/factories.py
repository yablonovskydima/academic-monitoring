from ml_service.schemas.student_semester_features import StudentSemesterFeatures


def make_features(**overrides) -> StudentSemesterFeatures:
    defaults = dict(
        student_id=1,
        semester_id=1,
        academic_year="2023/2024",
        term=1,
        course_year=1,
        study_mode="full_time",
        avg_grade=80.0,
        grade_stddev=10.0,
        total_sessions=100,
        absences_count=5,
        absence_percent=5.0,
        unworked_absences_count=1,
        lecture_absence_percent=5.0,
        lab_absence_percent=5.0,
        total_gradable_sessions=50,
        graded_sessions_count=50,
        missing_submissions_count=0,
        late_submissions_count=0,
        disappeared_next_semester=False,
        repeated_subjects_count=0,
        avg_grade_delta=0.0,
        absence_percent_delta=0.0,
        missing_submissions_delta=0,
        cumulative_avg_grade=80.0,
        cumulative_absence_percent=5.0,
        cumulative_avg_missing_submissions=0.0,
        cumulative_avg_late_submissions=0.0,
        semesters_completed_count=1,
    )
    defaults.update(overrides)
    return StudentSemesterFeatures(**defaults)
