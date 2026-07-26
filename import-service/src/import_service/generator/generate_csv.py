import csv
import random
from datetime import date, timedelta

from faker import Faker

from import_service.generator import config

fake = Faker("en_US")

_counters: dict[str, int] = {}


def _next_id(entity: str) -> int:
    _counters[entity] = _counters.get(entity, 0) + 1
    return _counters[entity]


def _clip_score(score: float) -> float:
    return round(max(0.0, min(100.0, score)), 2)

def generate_groups() -> list[dict]:
    groups = []
    for i in range(config.GROUPS_COUNT):
        groups.append({
            "id": i + 1,
            "name": f"CS-{20 + i}",
            "faculty": config.FACULTY,
            "course_year": random.randint(1, 4),
        })
    return groups


def generate_students(groups: list[dict]) -> list[dict]:
    students = []
    study_modes = list(config.STUDY_MODE_WEIGHTS.keys())
    weights = list(config.STUDY_MODE_WEIGHTS.values())

    student_id = 1
    for group in groups:
        for _ in range(config.STUDENTS_PER_GROUP):
            students.append({
                "id": student_id,
                "full_name": fake.name(),
                "group_id": group["id"],
                "email": fake.unique.email(),
                "study_mode": random.choices(study_modes, weights=weights)[0],
            })
            student_id += 1
    return students

def generate_semesters() -> list[dict]:
    semesters = []
    for academic_year in config.ACADEMIC_YEARS:
        start_year = int(academic_year.split("/")[0])
        semesters.append({
            "id": _next_id("semester"),
            "academic_year": academic_year,
            "term": 1,
            "start_date": date(start_year, 9, 1).isoformat(),
            "end_date": date(start_year + 1, 1, 20).isoformat(),
        })
        semesters.append({
            "id": _next_id("semester"),
            "academic_year": academic_year,
            "term": 2,
            "start_date": date(start_year + 1, 2, 1).isoformat(),
            "end_date": date(start_year + 1, 6, 20).isoformat(),
        })
    return semesters

def generate_teachers() -> list[dict]:
    return [
        {
            "id": _next_id("teacher"),
            "full_name": fake.name(),
            "department": config.TEACHER_DEPARTMENT,
        }
        for _ in range(config.TEACHERS_COUNT)
    ]


def generate_subjects() -> list[dict]:
    return [
        {
            "id": _next_id("subject"),
            "name": name,
            "is_elective": random.choice([True, False]),
        }
        for name in config.SUBJECT_NAMES
    ]

def generate_subject_offerings(semesters: list[dict], subjects: list[dict], teachers: list[dict]) -> list[dict]:
    offerings = []
    for semester in semesters:
        for subject in subjects:
            teacher = random.choice(teachers)
            offerings.append({
                "id": _next_id("subject_offering"),
                "subject_id": subject["id"],
                "semester_id": semester["id"],
                "teacher_id": teacher["id"],
                "max_practice_score": 50,
                "max_exam_score": 50,
            })
    return offerings

def generate_enrollments(students: list[dict], offerings: list[dict], semesters: list[dict]) -> list[dict]:
    enrollments = []
    offerings_by_semester = {
        semester["id"]: [o for o in offerings if o["semester_id"] == semester["id"]]
        for semester in semesters
    }

    for student in students:
        for semester in semesters:
            available = offerings_by_semester[semester["id"]]
            count = random.randint(*config.ENROLLMENTS_PER_STUDENT_PER_SEMESTER)
            count = min(count, len(available))
            chosen = random.sample(available, count)

            for offering in chosen:
                enrollments.append({
                    "id": _next_id("enrollment"),
                    "student_id": student["id"],
                    "subject_offering_id": offering["id"],
                    "enrolled_at": semester["start_date"],
                })
    return enrollments

def generate_class_sessions(offerings: list[dict], semesters_by_id: dict[int, dict]) -> list[dict]:
    sessions = []

    for offering in offerings:
        semester = semesters_by_id[offering["semester_id"]]
        start = date.fromisoformat(semester["start_date"])
        end = date.fromisoformat(semester["end_date"])

        for i in range(config.LECTURES_PER_OFFERING):
            sessions.append({
                "id": _next_id("class_session"),
                "subject_offering_id": offering["id"],
                "session_type": "lecture",
                "session_number": i + 1,
                "date": (start + timedelta(weeks=i)).isoformat(),
            })

        for i in range(config.LABS_PER_OFFERING):
            sessions.append({
                "id": _next_id("class_session"),
                "subject_offering_id": offering["id"],
                "session_type": "lab",
                "session_number": i + 1,
                "date": (start + timedelta(weeks=i, days=3)).isoformat(),
            })

        for i in range(config.CONTROLS_PER_OFFERING):
            fraction = (i + 1) / (config.CONTROLS_PER_OFFERING + 1)
            control_date = start + (end - start) * fraction
            sessions.append({
                "id": _next_id("class_session"),
                "subject_offering_id": offering["id"],
                "session_type": "control",
                "session_number": i + 1,
                "date": control_date.isoformat(),
            })

        sessions.append({
            "id": _next_id("class_session"),
            "subject_offering_id": offering["id"],
            "session_type": "exam",
            "session_number": 1,
            "date": (end - timedelta(days=3)).isoformat(),
        })

    return sessions

def generate_attendance(enrollments: list[dict], sessions_by_offering: dict[int, list[dict]],
                          students_by_id: dict[int, dict]) -> list[dict]:
    attendance = []

    for enrollment in enrollments:
        student = students_by_id[enrollment["student_id"]]
        sessions = sessions_by_offering.get(enrollment["subject_offering_id"], [])

        relevant_sessions = [s for s in sessions if s["session_type"] in ("lecture", "lab", "control")]

        absence_probability = config.ABSENCE_PROBABILITY[student["study_mode"]]
        is_excused_by_default = student["study_mode"] != "full_time"

        for session in relevant_sessions:
            is_absent = random.random() < absence_probability
            is_worked_off = is_absent and random.random() < config.WORKED_OFF_PROBABILITY_IF_ABSENT

            attendance.append({
                "id": _next_id("attendance"),
                "student_id": student["id"],
                "class_session_id": session["id"],
                "is_absent": is_absent,
                "is_worked_off": is_worked_off,
                "is_excused": is_excused_by_default,
            })

    return attendance

def generate_grades(enrollments: list[dict], sessions_by_offering: dict[int, list[dict]]) -> list[dict]:
    grades = []

    for enrollment in enrollments:
        sessions = sessions_by_offering.get(enrollment["subject_offering_id"], [])

        lab_sessions = sorted(
            [s for s in sessions if s["session_type"] == "lab"],
            key=lambda s: s["session_number"],
        )
        control_sessions = [s for s in sessions if s["session_type"] == "control"]
        exam_sessions = [s for s in sessions if s["session_type"] == "exam"]

        for i, session in enumerate(lab_sessions):
            session_date = date.fromisoformat(session["date"])
            if i + 1 < len(lab_sessions):
                deadline = date.fromisoformat(lab_sessions[i + 1]["date"])
            else:
                deadline = session_date + timedelta(days=7)

            is_late = random.random() < config.LATE_SUBMISSION_PROBABILITY
            graded_at = deadline + timedelta(days=random.randint(1, 5)) if is_late \
                else deadline - timedelta(days=random.randint(0, 3))

            score = _clip_score(random.gauss(config.SCORE_MEAN, config.SCORE_STDDEV))

            grades.append({
                "id": _next_id("grade"),
                "student_id": enrollment["student_id"],
                "class_session_id": session["id"],
                "score": score,
                "deadline_at": deadline.isoformat(),
                "graded_at": graded_at.isoformat(),
            })

        for session in control_sessions + exam_sessions:
            session_date = date.fromisoformat(session["date"])
            score = _clip_score(random.gauss(config.SCORE_MEAN, config.SCORE_STDDEV))

            grades.append({
                "id": _next_id("grade"),
                "student_id": enrollment["student_id"],
                "class_session_id": session["id"],
                "score": score,
                "deadline_at": session_date.isoformat(),
                "graded_at": session_date.isoformat(),
            })

    return grades

def write_csv(rows: list[dict], filename: str) -> None:
    if not rows:
        print(f"Skipped {filename} — no rows")
        return

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = config.DATA_DIR / filename

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Written {len(rows)} rows to {filepath}")


def run_generate():
    groups = generate_groups()
    write_csv(groups, "groups.csv")

    students = generate_students(groups)
    write_csv(students, "students.csv")

    semesters = generate_semesters()
    write_csv(semesters, "semesters.csv")

    teachers = generate_teachers()
    write_csv(teachers, "teachers.csv")

    subjects = generate_subjects()
    write_csv(subjects, "subjects.csv")

    offerings = generate_subject_offerings(semesters, subjects, teachers)
    write_csv(offerings, "subject_offerings.csv")

    enrollments = generate_enrollments(students, offerings, semesters)
    write_csv(enrollments, "enrollments.csv")

    semesters_by_id = {s["id"]: s for s in semesters}
    sessions = generate_class_sessions(offerings, semesters_by_id)
    write_csv(sessions, "class_sessions.csv")

    sessions_by_offering: dict[int, list[dict]] = {}
    for session in sessions:
        sessions_by_offering.setdefault(session["subject_offering_id"], []).append(session)

    students_by_id = {s["id"]: s for s in students}
    attendance = generate_attendance(enrollments, sessions_by_offering, students_by_id)
    write_csv(attendance, "attendance.csv")

    grades = generate_grades(enrollments, sessions_by_offering)
    write_csv(grades, "grades.csv")

    print("\nSummary:")
    print(f"  groups: {len(groups)}, students: {len(students)}")
    print(f"  semesters: {len(semesters)}, teachers: {len(teachers)}, subjects: {len(subjects)}")
    print(f"  subject_offerings: {len(offerings)}, enrollments: {len(enrollments)}")
    print(f"  class_sessions: {len(sessions)}, attendance: {len(attendance)}, grades: {len(grades)}")


if __name__ == "__main__":
    run_generate()