from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[3] / "data"

# groups / students

GROUPS_COUNT = 6
STUDENTS_PER_GROUP = 25
FACULTY = "Computer Science"

STUDY_MODE_WEIGHTS = {
    "full_time": 0.85,
    "part_time": 0.1,
    "individual_schedule": 0.05,
}

# semesters

ACADEMIC_YEARS = ["2022/2023", "2023/2024", "2024/2025"]

# teachers / subjects

TEACHERS_COUNT = 10
TEACHER_DEPARTMENT = "Department of Software"

SUBJECT_NAMES = [
    "Metaanalysis",
    "Databases",
    "Algorithms",
    "Web development",
    "Machine learning",
]

# subject offerings / class sessions

LECTURES_PER_OFFERING = 8
LABS_PER_OFFERING = 8
CONTROLS_PER_OFFERING = 2

# enrollments

ENROLLMENTS_PER_STUDENT_PER_SEMESTER = (3, 5)

# attendance

ABSENCE_PROBABILITY = {
    "full_time": 0.12,
    "part_time": 0.0,
    "individual_schedule": 0.0,
}
WORKED_OFF_PROBABILITY_IF_ABSENT = 0.4

# grades

SCORE_MEAN = 75
SCORE_STDDEV = 15
LATE_SUBMISSION_PROBABILITY = 0.15