from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


# ---------- groups / students ----------

GROUPS_COUNT = 80
STUDENTS_PER_GROUP = 25
FACULTY = "Computer Science"

STUDY_MODE_WEIGHTS = {
    "full_time": 0.85,
    "part_time": 0.10,
    "individual_schedule": 0.05,
}


# ---------- synthetic student risk profiles ----------
#
# These profiles are used only by the generator to create meaningful
# relationships between student behavior and ML targets.
#
# risk_profile is NOT written to students.csv.

RISK_PROFILE_WEIGHTS = {
    "normal": 0.70,
    "admission_risk": 0.08,
    "debt_risk": 0.10,
    "expulsion_risk": 0.08,
    "admission_and_expulsion_risk": 0.04,
}


RISK_PROFILE_SETTINGS = {
    "normal": {
        "absence_probability": 0.12,
        "score_mean": 75.0,
        "score_stddev": 15.0,
        "late_submission_probability": 0.15,
    },

    "admission_risk": {
        # Intentionally very high so that lecture/lab absence
        # exceeds the 75% admission threshold in many cases.
        "absence_probability": 0.82,
        "score_mean": 62.0,
        "score_stddev": 15.0,
        "late_submission_probability": 0.30,
    },

    "debt_risk": {
        "absence_probability": 0.30,
        "score_mean": 52.0,
        "score_stddev": 18.0,
        "late_submission_probability": 0.35,
    },

    "expulsion_risk": {
        "absence_probability": 0.55,
        "score_mean": 48.0,
        "score_stddev": 20.0,
        "late_submission_probability": 0.45,
    },

    "admission_and_expulsion_risk": {
        "absence_probability": 0.85,
        "score_mean": 45.0,
        "score_stddev": 20.0,
        "late_submission_probability": 0.50,
    },
}


# ---------- semesters ----------

ACADEMIC_YEARS = [
    "2023/2024",
    "2024/2025",
    "2025/2026",
]


# ---------- teachers / subjects ----------

TEACHERS_COUNT = 40
TEACHER_DEPARTMENT = "Software Engineering Department"

SUBJECT_NAMES = [
    "Calculus",
    "Databases",
    "Algorithms",
    "Operating Systems",
    "Web Development",
    "Machine Learning",
]


# ---------- subject offerings / class sessions ----------

LECTURES_PER_OFFERING = 8
LABS_PER_OFFERING = 8
CONTROLS_PER_OFFERING = 2


# ---------- enrollments ----------

ENROLLMENTS_PER_STUDENT_PER_SEMESTER = (3, 5)

# Number of subjects a debt-risk student should try to repeat
# from the previous semester.
DEBT_REPEATED_SUBJECTS_RANGE = (1, 2)


# ---------- attendance ----------

# Kept for compatibility / normal students.
# Risk profiles override these values.
ABSENCE_PROBABILITY = {
    "full_time": 0.12,
    "part_time": 0.0,
    "individual_schedule": 0.0,
}

WORKED_OFF_PROBABILITY_IF_ABSENT = 0.4


# ---------- grades ----------

SCORE_MEAN = 75
SCORE_STDDEV = 15
LATE_SUBMISSION_PROBABILITY = 0.15


# ---------- dropout ----------

DROPOUT_RATE = 0.04