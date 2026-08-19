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
        "absence_probability_spread": 0.08,
        "score_mean": 75.0,
        "score_mean_spread": 10.0,
        "score_stddev": 15.0,
        "late_submission_probability": 0.15,
    },

    "admission_risk": {
        "absence_probability": 0.82,
        "absence_probability_spread": 0.10,
        "score_mean": 62.0,
        "score_mean_spread": 10.0,
        "score_stddev": 15.0,
        "late_submission_probability": 0.30,
    },

    "debt_risk": {
        "absence_probability": 0.30,
        "absence_probability_spread": 0.10,
        "score_mean": 52.0,
        "score_mean_spread": 10.0,
        "score_stddev": 18.0,
        "late_submission_probability": 0.35,
    },

    "expulsion_risk": {
        "absence_probability": 0.55,
        "absence_probability_spread": 0.12,
        "score_mean": 48.0,
        "score_mean_spread": 10.0,
        "score_stddev": 20.0,
        "late_submission_probability": 0.45,
    },

    "admission_and_expulsion_risk": {
        "absence_probability": 0.85,
        "absence_probability_spread": 0.10,
        "score_mean": 45.0,
        "score_mean_spread": 10.0,
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

# One list per semester position (1..6 across the 3-year window).
# Each student's normal course load for a given semester is drawn
# only from that semester's own list, so two consecutive semesters
# share almost no subjects by construction — any overlap a student
# ends up with is (almost) always the deliberate debt-risk repeat
# below, not incidental random selection from a shared pool.
#
# Subject names may repeat across positions (e.g. "English for IT I"
# / "English for IT II") to reflect multi-part courses — each is
# still a distinct subject with its own offering.
CURRICULUM = [
    [
        "Calculus I",
        "Discrete Mathematics",
        "Introduction to Programming",
        "Computer Architecture",
        "English for IT I",
        "Academic Writing",
        "Physical Education I",
    ],
    [
        "Calculus II",
        "Linear Algebra",
        "Object-Oriented Programming",
        "Data Structures",
        "English for IT II",
        "Probability and Statistics",
        "Physical Education II",
    ],
    [
        "Algorithms and Complexity",
        "Databases",
        "Computer Networks",
        "Software Engineering Principles",
        "Web Development",
        "Operating Systems",
        "Technical English",
    ],
    [
        "Advanced Databases",
        "Operating Systems Internals",
        "Distributed Systems",
        "Human-Computer Interaction",
        "Mobile Development",
        "Numerical Methods",
        "Elective I",
    ],
    [
        "Machine Learning",
        "Compiler Construction",
        "Information Security",
        "Cloud Computing",
        "Data Mining",
        "Project Management",
        "Elective II",
    ],
    [
        "Deep Learning",
        "Software Architecture",
        "DevOps Practices",
        "Big Data Systems",
        "Capstone Project",
        "Business Analysis",
        "Elective III",
    ],
]


# ---------- subject offerings / class sessions ----------

LECTURES_PER_OFFERING = 8
LABS_PER_OFFERING = 8
CONTROLS_PER_OFFERING = 2


# ---------- enrollments ----------

# ~7 subjects/semester are offered (see CURRICULUM), so this is
# effectively clamped to "take (almost) the whole semester's load".
ENROLLMENTS_PER_STUDENT_PER_SEMESTER = (6, 8)

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

SEMESTER_SCORE_DRIFT_STDDEV = 5.0
SEMESTER_ABSENCE_DRIFT_STDDEV = 0.05


# ---------- grades ----------

SCORE_MEAN = 75
SCORE_STDDEV = 15
LATE_SUBMISSION_PROBABILITY = 0.15


# ---------- dropout ----------

DROPOUT_RATE = 0.3