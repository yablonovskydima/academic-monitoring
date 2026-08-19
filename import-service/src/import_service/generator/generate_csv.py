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


def _get_profile_settings(student: dict) -> dict:
    profile = student.get("risk_profile", "normal")
    return config.RISK_PROFILE_SETTINGS[profile]


def _get_semester_absence_probability(
    student: dict,
    semester_id: int,
    cache: dict[tuple[int, int], float],
) -> float:
    if student["study_mode"] != "full_time":
        return config.ABSENCE_PROBABILITY[student["study_mode"]]

    key = (student["id"], semester_id)

    if key not in cache:
        cache[key] = min(1.0, max(0.0, random.gauss(
            student["risk_absence_probability"],
            config.SEMESTER_ABSENCE_DRIFT_STDDEV,
        )))

    return cache[key]


def _get_semester_score_parameters(
    student: dict,
    semester_id: int,
    cache: dict[tuple[int, int], float],
) -> tuple[float, float]:
    settings = _get_profile_settings(student)
    key = (student["id"], semester_id)

    if key not in cache:
        cache[key] = min(100.0, max(0.0, random.gauss(
            student["risk_score_mean"],
            config.SEMESTER_SCORE_DRIFT_STDDEV,
        )))

    return cache[key], settings["score_stddev"]


def _get_late_submission_probability(student: dict) -> float:
    return _get_profile_settings(student)["late_submission_probability"]


# ---------------------------------------------------------------------------
# Groups / students
# ---------------------------------------------------------------------------

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
    study_mode_weights = list(config.STUDY_MODE_WEIGHTS.values())

    risk_profiles = list(config.RISK_PROFILE_WEIGHTS.keys())
    risk_profile_weights = list(config.RISK_PROFILE_WEIGHTS.values())

    student_id = 1

    for group in groups:
        for _ in range(config.STUDENTS_PER_GROUP):
            study_mode = random.choices(
                study_modes,
                weights=study_mode_weights,
            )[0]

            risk_profile = random.choices(
                risk_profiles,
                weights=risk_profile_weights,
            )[0]

            # Admission denial only applies to full-time students.
            #
            # If a part-time / individual-schedule student was randomly
            # assigned an admission-related profile, convert it to another
            # meaningful risk profile.
            if study_mode != "full_time":
                if risk_profile == "admission_risk":
                    risk_profile = "debt_risk"

                elif risk_profile == "admission_and_expulsion_risk":
                    risk_profile = "expulsion_risk"

            settings = config.RISK_PROFILE_SETTINGS[risk_profile]

            risk_score_mean = min(100.0, max(0.0, random.gauss(
                settings["score_mean"],
                settings["score_mean_spread"],
            )))

            risk_absence_probability = min(1.0, max(0.0, random.gauss(
                settings["absence_probability"],
                settings["absence_probability_spread"],
            )))

            students.append({
                "id": student_id,
                "full_name": fake.name(),
                "group_id": group["id"],
                "email": fake.unique.email(),
                "study_mode": study_mode,
                "risk_profile": risk_profile,
                "risk_score_mean": risk_score_mean,
                "risk_absence_probability": risk_absence_probability,
            })

            student_id += 1

    return students


# ---------------------------------------------------------------------------
# Semesters
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Teachers / subjects
# ---------------------------------------------------------------------------

def generate_teachers() -> list[dict]:
    return [
        {
            "id": _next_id("teacher"),
            "full_name": fake.name(),
            "department": config.TEACHER_DEPARTMENT,
        }
        for _ in range(config.TEACHERS_COUNT)
    ]


def generate_subjects() -> tuple[list[dict], list[list[int]]]:
    """
    Returns (subjects, subject_ids_by_position).

    subject_ids_by_position[i] holds the subject ids that belong to
    semester position i (config.CURRICULUM[i]), so the offering step
    knows which subjects are natively offered in which semester.
    """
    subjects = []
    subject_ids_by_position: list[list[int]] = []

    for position_names in config.CURRICULUM:
        position_ids = []

        for name in position_names:
            subject = {
                "id": _next_id("subject"),
                "name": name,
                "is_elective": random.choice([True, False]),
            }
            subjects.append(subject)
            position_ids.append(subject["id"])

        subject_ids_by_position.append(position_ids)

    return subjects, subject_ids_by_position


# ---------------------------------------------------------------------------
# Subject offerings
# ---------------------------------------------------------------------------

def generate_subject_offerings(
    semesters: list[dict],
    subject_ids_by_position: list[list[int]],
    teachers: list[dict],
) -> list[dict]:
    """
    Create one offering per subject in its OWN semester position only
    (semesters[i] <-> config.CURRICULUM[i]), not in every semester.
    """
    offerings = []

    for position, semester in enumerate(semesters):
        for subject_id in subject_ids_by_position[position]:
            teacher = random.choice(teachers)

            offerings.append({
                "id": _next_id("subject_offering"),
                "subject_id": subject_id,
                "semester_id": semester["id"],
                "teacher_id": teacher["id"],
                "max_practice_score": 50,
                "max_exam_score": 50,
            })

    return offerings


# ---------------------------------------------------------------------------
# Enrollments
# ---------------------------------------------------------------------------

def generate_enrollments(
    students: list[dict],
    offerings: list[dict],
    semesters: list[dict],
    teachers: list[dict],
) -> tuple[list[dict], list[dict]]:
    """
    Generate student enrollments. Returns (enrollments, offerings) —
    offerings is extended with any retake offerings created below, so
    callers must use the returned list, not the one passed in.

    Normal students:
        subjects are selected randomly from that semester's own
        curriculum position (see config.CURRICULUM) — subjects are
        NOT shared across semesters, so this never accidentally
        produces a repeat.

    Debt-risk students:
        from the second semester onward, 1-2 subjects from the previous
        semester are intentionally repeated. Since a subject normally
        only has an offering in its own semester position, repeating
        one means creating a one-off "retake" offering for it here.

    This creates real positive examples for:

        repeated_subjects_count > 0

    without adding any fake ML-specific fields to the generated data.
    """
    enrollments = []
    all_offerings = list(offerings)

    offerings_by_semester: dict[int, list[dict]] = {
        semester["id"]: [
            offering
            for offering in offerings
            if offering["semester_id"] == semester["id"]
        ]
        for semester in semesters
    }

    previous_subjects_by_student: dict[int, set[int]] = {}

    for semester_index, semester in enumerate(semesters):
        semester_id = semester["id"]
        available = offerings_by_semester[semester_id]

        offering_by_subject = {
            offering["subject_id"]: offering
            for offering in available
        }
        retake_offering_by_subject: dict[int, dict] = {}

        for student in students:
            student_id = student["id"]

            min_count, max_count = config.ENROLLMENTS_PER_STUDENT_PER_SEMESTER
            count = random.randint(min_count, max_count)
            count = min(count, len(available))

            risk_profile = student.get("risk_profile", "normal")

            previous_subjects = previous_subjects_by_student.get(
                student_id,
                set(),
            )

            selected_subject_ids: set[int] = set()

            # ---------------------------------------------------------------
            # Debt-risk students intentionally repeat subjects.
            # ---------------------------------------------------------------

            if (
                semester_index > 0
                and risk_profile == "debt_risk"
                and previous_subjects
            ):
                repeat_min, repeat_max = (
                    config.DEBT_REPEATED_SUBJECTS_RANGE
                )

                repeat_count = random.randint(
                    repeat_min,
                    min(repeat_max, count, len(previous_subjects)),
                )

                repeated_subjects = random.sample(
                    list(previous_subjects),
                    repeat_count,
                )

                for subject_id in repeated_subjects:
                    if (
                        subject_id in offering_by_subject
                        or subject_id in retake_offering_by_subject
                    ):
                        continue

                    teacher = random.choice(teachers)
                    retake_offering = {
                        "id": _next_id("subject_offering"),
                        "subject_id": subject_id,
                        "semester_id": semester_id,
                        "teacher_id": teacher["id"],
                        "max_practice_score": 50,
                        "max_exam_score": 50,
                    }

                    all_offerings.append(retake_offering)
                    retake_offering_by_subject[subject_id] = retake_offering

                selected_subject_ids.update(repeated_subjects)

            # ---------------------------------------------------------------
            # Fill the remaining enrollment slots randomly.
            # ---------------------------------------------------------------

            remaining_subject_ids = [
                offering["subject_id"]
                for offering in available
                if offering["subject_id"] not in selected_subject_ids
            ]

            remaining_count = count - len(selected_subject_ids)

            if remaining_count > 0:
                selected_subject_ids.update(
                    random.sample(
                        remaining_subject_ids,
                        remaining_count,
                    )
                )

            # ---------------------------------------------------------------
            # Create enrollments.
            # ---------------------------------------------------------------

            for subject_id in selected_subject_ids:
                offering = (
                    offering_by_subject.get(subject_id)
                    or retake_offering_by_subject[subject_id]
                )

                enrollments.append({
                    "id": _next_id("enrollment"),
                    "student_id": student_id,
                    "subject_offering_id": offering["id"],
                    "enrolled_at": semester["start_date"],
                })

            previous_subjects_by_student[student_id] = (
                selected_subject_ids
            )

    return enrollments, all_offerings


# ---------------------------------------------------------------------------
# Class sessions
# ---------------------------------------------------------------------------

def generate_class_sessions(
    offerings: list[dict],
    semesters_by_id: dict[int, dict],
) -> list[dict]:
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
                "date": (
                    start + timedelta(weeks=i)
                ).isoformat(),
            })

        # Labs
        for i in range(config.LABS_PER_OFFERING):
            sessions.append({
                "id": _next_id("class_session"),
                "subject_offering_id": offering["id"],
                "session_type": "lab",
                "session_number": i + 1,
                "date": (
                    start + timedelta(weeks=i, days=3)
                ).isoformat(),
            })

        for i in range(config.CONTROLS_PER_OFFERING):
            fraction = (
                (i + 1)
                / (config.CONTROLS_PER_OFFERING + 1)
            )

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
            "date": (
                end - timedelta(days=3)
            ).isoformat(),
        })

    return sessions


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------

def generate_attendance(
    enrollments: list[dict],
    sessions_by_offering: dict[int, list[dict]],
    students_by_id: dict[int, dict],
    semester_id_by_offering: dict[int, int],
) -> list[dict]:
    attendance = []
    drift_cache: dict[tuple[int, int], float] = {}

    for enrollment in enrollments:
        student = students_by_id[enrollment["student_id"]]

        sessions = sessions_by_offering.get(
            enrollment["subject_offering_id"],
            [],
        )

        relevant_sessions = [
            session
            for session in sessions
            if session["session_type"] in ("lecture", "lab", "control")
        ]

        semester_id = semester_id_by_offering[enrollment["subject_offering_id"]]
        absence_probability = _get_semester_absence_probability(
            student, semester_id, drift_cache,
        )

        is_excused_by_default = (
            student["study_mode"] != "full_time"
        )

        for session in relevant_sessions:
            is_absent = (
                random.random() < absence_probability
            )

            is_worked_off = (
                is_absent
                and random.random()
                < config.WORKED_OFF_PROBABILITY_IF_ABSENT
            )

            attendance.append({
                "id": _next_id("attendance"),
                "student_id": student["id"],
                "class_session_id": session["id"],
                "is_absent": is_absent,
                "is_worked_off": is_worked_off,
                "is_excused": is_excused_by_default,
            })

    return attendance


# ---------------------------------------------------------------------------
# Grades
# ---------------------------------------------------------------------------

def generate_grades(
    enrollments: list[dict],
    sessions_by_offering: dict[int, list[dict]],
    students_by_id: dict[int, dict],
    semester_id_by_offering: dict[int, int],
) -> list[dict]:
    grades = []
    drift_cache: dict[tuple[int, int], float] = {}

    for enrollment in enrollments:
        student = students_by_id[enrollment["student_id"]]

        sessions = sessions_by_offering.get(
            enrollment["subject_offering_id"],
            [],
        )

        lab_sessions = sorted(
            [
                session
                for session in sessions
                if session["session_type"] == "lab"
            ],
            key=lambda session: session["session_number"],
        )

        control_sessions = [
            session
            for session in sessions
            if session["session_type"] == "control"
        ]

        exam_sessions = [
            session
            for session in sessions
            if session["session_type"] == "exam"
        ]

        semester_id = semester_id_by_offering[enrollment["subject_offering_id"]]
        score_mean, score_stddev = _get_semester_score_parameters(
            student, semester_id, drift_cache,
        )
        late_probability = _get_late_submission_probability(student)

        # ---------------------------------------------------------------
        # Lab submissions
        # ---------------------------------------------------------------

        for i, session in enumerate(lab_sessions):
            session_date = date.fromisoformat(session["date"])

            if i + 1 < len(lab_sessions):
                deadline = date.fromisoformat(
                    lab_sessions[i + 1]["date"]
                )
            else:
                deadline = session_date + timedelta(days=7)

            is_late = (
                random.random() < late_probability
            )

            if is_late:
                graded_at = (
                    deadline
                    + timedelta(days=random.randint(1, 5))
                )
            else:
                graded_at = (
                    deadline
                    - timedelta(days=random.randint(0, 3))
                )

            score = _clip_score(
                random.gauss(
                    score_mean,
                    score_stddev,
                )
            )

            grades.append({
                "id": _next_id("grade"),
                "student_id": enrollment["student_id"],
                "class_session_id": session["id"],
                "score": score,
                "deadline_at": deadline.isoformat(),
                "graded_at": graded_at.isoformat(),
            })

        # ---------------------------------------------------------------
        # Controls + exams
        # ---------------------------------------------------------------

        for session in control_sessions + exam_sessions:
            session_date = date.fromisoformat(
                session["date"]
            )

            score = _clip_score(
                random.gauss(
                    score_mean,
                    score_stddev,
                )
            )

            grades.append({
                "id": _next_id("grade"),
                "student_id": enrollment["student_id"],
                "class_session_id": session["id"],
                "score": score,
                "deadline_at": session_date.isoformat(),
                "graded_at": session_date.isoformat(),
            })

    return grades


# ---------------------------------------------------------------------------
# Dropout
# ---------------------------------------------------------------------------

def apply_dropout(
    students: list[dict],
    enrollments: list[dict],
    offerings: list[dict],
    semesters: list[dict],
) -> list[dict]:
    """
    Remove enrollments from the dropout semester onward.

    Expulsion-risk students are preferred when selecting dropout students.

    This makes the generated data causally meaningful:

        poor student behavior
                ↓
        expulsion-risk profile
                ↓
        dropout
                ↓
        disappeared_next_semester = True
    """
    dropout_count = int(
        len(students) * config.DROPOUT_RATE
    )

    if dropout_count == 0:
        return enrollments

    preferred_students = [
        student
        for student in students
        if student.get("risk_profile") in {
            "expulsion_risk",
            "admission_and_expulsion_risk",
        }
    ]

    if len(preferred_students) >= dropout_count:
        dropout_students = random.sample(
            preferred_students,
            dropout_count,
        )

    else:
        preferred_ids = {
            student["id"]
            for student in preferred_students
        }

        remaining_students = [
            student
            for student in students
            if student["id"] not in preferred_ids
        ]

        additional_count = (
            dropout_count
            - len(preferred_students)
        )

        additional_students = random.sample(
            remaining_students,
            min(
                additional_count,
                len(remaining_students),
            ),
        )

        dropout_students = (
            preferred_students
            + additional_students
        )

    dropout_student_ids = {
        student["id"]
        for student in dropout_students
    }

    semester_ids_ordered = [
        semester["id"]
        for semester in semesters
    ]

    offering_semester_map = {
        offering["id"]: offering["semester_id"]
        for offering in offerings
    }

    drop_semester_by_student: dict[int, int] = {}

    for student_id in dropout_student_ids:
        drop_index = random.randint(
            1,
            len(semester_ids_ordered) - 1,
        )

        drop_semester_by_student[student_id] = (
            semester_ids_ordered[drop_index]
        )

    filtered = []

    for enrollment in enrollments:
        student_id = enrollment["student_id"]

        if student_id in dropout_student_ids:
            enrollment_semester_id = offering_semester_map[
                enrollment["subject_offering_id"]
            ]

            drop_semester_id = drop_semester_by_student[
                student_id
            ]

            if enrollment_semester_id >= drop_semester_id:
                continue

        filtered.append(enrollment)

    return filtered


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def write_csv(
    rows: list[dict],
    filename: str,
) -> None:
    if not rows:
        print(f"Skipped {filename} — no rows")
        return

    config.DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    filepath = config.DATA_DIR / filename

    output_rows = []

    internal_fields = {"risk_profile", "risk_score_mean", "risk_absence_probability"}

    for row in rows:
        output_rows.append({
            key: value
            for key, value in row.items()
            if key not in internal_fields
        })

    with open(
        filepath,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=output_rows[0].keys(),
        )

        writer.writeheader()
        writer.writerows(output_rows)

    print(
        f"Written {len(output_rows)} rows to {filepath}"
    )


# ---------------------------------------------------------------------------
# Main generation flow
# ---------------------------------------------------------------------------

def run_generate():
    groups = generate_groups()
    write_csv(
        groups,
        "groups.csv",
    )

    students = generate_students(groups)
    write_csv(
        students,
        "students.csv",
    )

    semesters = generate_semesters()
    write_csv(
        semesters,
        "semesters.csv",
    )

    teachers = generate_teachers()
    write_csv(
        teachers,
        "teachers.csv",
    )

    subjects, subject_ids_by_position = generate_subjects()
    write_csv(
        subjects,
        "subjects.csv",
    )

    offerings = generate_subject_offerings(
        semesters,
        subject_ids_by_position,
        teachers,
    )

    enrollments, offerings = generate_enrollments(
        students,
        offerings,
        semesters,
        teachers,
    )

    write_csv(
        offerings,
        "subject_offerings.csv",
    )

    enrollments = apply_dropout(
        students,
        enrollments,
        offerings,
        semesters,
    )

    write_csv(
        enrollments,
        "enrollments.csv",
    )

    semesters_by_id = {
        semester["id"]: semester
        for semester in semesters
    }

    sessions = generate_class_sessions(
        offerings,
        semesters_by_id,
    )

    write_csv(
        sessions,
        "class_sessions.csv",
    )

    sessions_by_offering: dict[int, list[dict]] = {}

    for session in sessions:
        sessions_by_offering.setdefault(
            session["subject_offering_id"],
            [],
        ).append(session)

    students_by_id = {
        student["id"]: student
        for student in students
    }

    semester_id_by_offering = {
        offering["id"]: offering["semester_id"]
        for offering in offerings
    }

    attendance = generate_attendance(
        enrollments,
        sessions_by_offering,
        students_by_id,
        semester_id_by_offering,
    )

    write_csv(
        attendance,
        "attendance.csv",
    )

    grades = generate_grades(
        enrollments,
        sessions_by_offering,
        students_by_id,
        semester_id_by_offering,
    )

    write_csv(
        grades,
        "grades.csv",
    )

    print("\nSummary:")
    print(
        f"  groups: {len(groups)}, "
        f"students: {len(students)}"
    )

    print(
        f"  semesters: {len(semesters)}, "
        f"teachers: {len(teachers)}, "
        f"subjects: {len(subjects)}"
    )

    print(
        f"  subject_offerings: {len(offerings)}, "
        f"enrollments: {len(enrollments)}"
    )

    print(
        f"  class_sessions: {len(sessions)}, "
        f"attendance: {len(attendance)}, "
        f"grades: {len(grades)}"
    )

    print(
        "  dropout applied to ~"
        f"{int(len(students) * config.DROPOUT_RATE)} "
        "students"
    )


if __name__ == "__main__":
    run_generate()