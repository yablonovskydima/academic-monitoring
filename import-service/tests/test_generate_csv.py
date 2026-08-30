import random

from import_service.generator.generate_csv import (
    apply_dropout,
    generate_enrollments,
    generate_subject_offerings,
    generate_subjects,
)


def make_teachers(n=3):
    return [{"id": i + 1, "full_name": f"Teacher {i}", "department": "X"} for i in range(n)]


def make_semesters(n):
    return [
        {
            "id": i + 1,
            "academic_year": "2023/2024",
            "term": (i % 2) + 1,
            "start_date": f"2023-{i + 1:02d}-01",
            "end_date": f"2023-{i + 1:02d}-28",
        }
        for i in range(n)
    ]


def make_students(n, debt_risk_ids=()):
    return [
        {
            "id": i + 1,
            "full_name": f"Student {i}",
            "group_id": 1,
            "email": f"s{i}@test.com",
            "study_mode": "full_time",
            "risk_profile": "debt_risk" if (i + 1) in debt_risk_ids else "normal",
        }
        for i in range(n)
    ]


def build_subjects_by_student_semester(enrollments, offerings):
    offering_by_id = {o["id"]: o for o in offerings}
    result: dict[tuple[int, int], set[int]] = {}

    for e in enrollments:
        offering = offering_by_id[e["subject_offering_id"]]
        key = (e["student_id"], offering["semester_id"])
        result.setdefault(key, set()).add(offering["subject_id"])

    return result


def test_each_subject_has_exactly_one_native_offering():
    semesters = make_semesters(3)
    teachers = make_teachers()

    subjects, subject_ids_by_position = generate_subjects()
    offerings = generate_subject_offerings(semesters, subject_ids_by_position, teachers)

    offering_counts: dict[int, int] = {}
    for offering in offerings:
        offering_counts[offering["subject_id"]] = offering_counts.get(offering["subject_id"], 0) + 1

    assert all(count == 1 for count in offering_counts.values())


def test_normal_students_never_get_an_accidental_repeated_subject():
    random.seed(0)
    semesters = make_semesters(3)
    teachers = make_teachers()
    students = make_students(10)  # all "normal"

    subjects, subject_ids_by_position = generate_subjects()
    offerings = generate_subject_offerings(semesters, subject_ids_by_position, teachers)
    enrollments, offerings = generate_enrollments(students, offerings, semesters, teachers)

    subjects_by_key = build_subjects_by_student_semester(enrollments, offerings)

    for student in students:
        for i in range(len(semesters) - 1):
            current = subjects_by_key.get((student["id"], semesters[i]["id"]), set())
            following = subjects_by_key.get((student["id"], semesters[i + 1]["id"]), set())
            assert current & following == set(), (
                f"student {student['id']} accidentally repeated a subject between "
                f"semester {semesters[i]['id']} and {semesters[i + 1]['id']}"
            )


def test_debt_risk_students_deliberately_repeat_a_subject():
    random.seed(0)
    semesters = make_semesters(3)
    teachers = make_teachers()
    students = make_students(5, debt_risk_ids={1})

    subjects, subject_ids_by_position = generate_subjects()
    offerings = generate_subject_offerings(semesters, subject_ids_by_position, teachers)
    enrollments, offerings = generate_enrollments(students, offerings, semesters, teachers)

    subjects_by_key = build_subjects_by_student_semester(enrollments, offerings)

    repeated_any = any(
        subjects_by_key.get((1, semesters[i]["id"]), set())
        & subjects_by_key.get((1, semesters[i + 1]["id"]), set())
        for i in range(len(semesters) - 1)
    )
    assert repeated_any


def test_dropout_never_removes_a_students_first_semester():
    random.seed(1)
    semesters = make_semesters(6)
    teachers = make_teachers()
    students = make_students(30)

    subjects, subject_ids_by_position = generate_subjects()
    offerings = generate_subject_offerings(semesters, subject_ids_by_position, teachers)
    enrollments, offerings = generate_enrollments(students, offerings, semesters, teachers)

    enrollments = apply_dropout(students, enrollments, offerings, semesters)

    offering_by_id = {o["id"]: o for o in offerings}
    semesters_by_student: dict[int, set[int]] = {}
    for e in enrollments:
        semester_id = offering_by_id[e["subject_offering_id"]]["semester_id"]
        semesters_by_student.setdefault(e["student_id"], set()).add(semester_id)

    first_semester_id = semesters[0]["id"]
    for student_id, student_semesters in semesters_by_student.items():
        assert first_semester_id in student_semesters
