from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[3] / "data"

GROUPS_COUNT = 6
STUDENTS_PER_GROUP = 25
FACULTY = "Комп'ютерні науки"

STUDY_MODE_WEIGHTS = {
    "full_time": 0.85,
    "part_time": 0.1,
    "individual_schedule": 0.05,
}