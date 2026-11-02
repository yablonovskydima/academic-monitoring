import random

from import_service.generator import config
from import_service.generator.generate_csv import (
    apply_dropout,
    generate_class_sessions,
    generate_enrollments,
    generate_grades,
    generate_groups,
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


def make_students(n, failing_ids=()):
    return [
        {
            "id": i + 1,
            "full_name": f"Student {i}",
            "group_id": 1,
            "email": f"s{i}@test.com",
            "study_mode": "full_time",
            "risk_profile": "normal",
            "risk_score_mean": 20.0 if (i + 1) in failing_ids else 95.0,
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


def test_students_who_pass_everything_never_repeat_a_subject():
    random.seed(0)
    semesters = make_semesters(3)
    teachers = make_teachers()
    students = make_students(10)

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


def test_students_who_fail_retake_subjects():
    random.seed(0)
    semesters = make_semesters(3)
    teachers = make_teachers()
    students = make_students(5, failing_ids={1})

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


def test_every_retaken_subject_was_failed_the_semester_before():
    random.seed(3)
    semesters = make_semesters(4)
    teachers = make_teachers()
    students = [
        {**s, "risk_score_mean": random.uniform(35.0, 80.0)}
        for s in make_students(40)
    ]

    subjects, subject_ids_by_position = generate_subjects()
    offerings = generate_subject_offerings(semesters, subject_ids_by_position, teachers)
    enrollments, offerings = generate_enrollments(students, offerings, semesters, teachers)

    offering_by_id = {o["id"]: o for o in offerings}
    score_by_key = {
        (e["student_id"], offering_by_id[e["subject_offering_id"]]["semester_id"],
         offering_by_id[e["subject_offering_id"]]["subject_id"]): e["score_mean"]
        for e in enrollments
    }
    subjects_by_key = build_subjects_by_student_semester(enrollments, offerings)

    retakes = 0
    for student in students:
        for i in range(len(semesters) - 1):
            current_id, next_id = semesters[i]["id"], semesters[i + 1]["id"]
            for subject_id in subjects_by_key[(student["id"], current_id)] & subjects_by_key[(student["id"], next_id)]:
                retakes += 1
                assert score_by_key[(student["id"], current_id, subject_id)] < config.PASS_SCORE

    assert retakes > 0


def test_failed_subjects_are_not_always_retaken():
    random.seed(4)
    semesters = make_semesters(2)
    teachers = make_teachers()
    students = make_students(30, failing_ids=set(range(1, 31)))

    subjects, subject_ids_by_position = generate_subjects()
    offerings = generate_subject_offerings(semesters, subject_ids_by_position, teachers)
    enrollments, offerings = generate_enrollments(students, offerings, semesters, teachers)

    subjects_by_key = build_subjects_by_student_semester(enrollments, offerings)
    failed = sum(len(subjects_by_key[(s["id"], semesters[0]["id"])]) for s in students)
    retaken = sum(
        len(subjects_by_key[(s["id"], semesters[0]["id"])] & subjects_by_key[(s["id"], semesters[1]["id"])])
        for s in students
    )

    assert 0 < retaken < failed


def test_grades_follow_the_subjects_score_level():
    random.seed(5)
    semesters = make_semesters(1)
    offering = {"id": 1, "subject_id": 1, "semester_id": semesters[0]["id"]}
    sessions = generate_class_sessions([offering], {s["id"]: s for s in semesters})
    student = {**make_students(1)[0], "risk_profile": "normal"}
    enrollments = [
        {"id": 1, "student_id": 1, "subject_offering_id": 1, "score_mean": 30.0},
        {"id": 2, "student_id": 1, "subject_offering_id": 1, "score_mean": 90.0},
    ]

    grades = [
        generate_grades([e], {1: sessions}, {1: student}, {1: semesters[0]["id"]})
        for e in enrollments
    ]
    failing_avg, passing_avg = (sum(g["score"] for g in gs) / len(gs) for gs in grades)

    assert failing_avg < config.PASS_SCORE < passing_avg


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


def _grades_for(profile, n_students=20):
    random.seed(2)
    semesters = make_semesters(1)
    teachers = make_teachers()
    students = [{**s, "risk_profile": profile, "risk_score_mean": 70.0} for s in make_students(n_students)]

    subjects, subject_ids_by_position = generate_subjects()
    offerings = generate_subject_offerings(semesters, subject_ids_by_position, teachers)
    enrollments, offerings = generate_enrollments(students, offerings, semesters, teachers)
    sessions = generate_class_sessions(offerings, {s["id"]: s for s in semesters})

    sessions_by_offering: dict[int, list[dict]] = {}
    for session in sessions:
        sessions_by_offering.setdefault(session["subject_offering_id"], []).append(session)

    grades = generate_grades(
        enrollments,
        sessions_by_offering,
        {s["id"]: s for s in students},
        {o["id"]: o["semester_id"] for o in offerings},
    )

    type_by_session = {s["id"]: s["session_type"] for s in sessions}
    expected = {
        session_type: sum(
            1
            for e in enrollments
            for s in sessions_by_offering[e["subject_offering_id"]]
            if s["session_type"] == session_type
        )
        for session_type in ("lab", "control", "exam")
    }
    graded = {
        session_type: sum(1 for g in grades if type_by_session[g["class_session_id"]] == session_type)
        for session_type in ("lab", "control", "exam")
    }
    return expected, graded


def test_some_lab_and_control_submissions_are_missing():
    expected, graded = _grades_for("expulsion_risk")

    assert graded["lab"] < expected["lab"]
    assert graded["control"] < expected["control"]


def test_exams_are_never_skipped():
    expected, graded = _grades_for("expulsion_risk")

    assert graded["exam"] == expected["exam"]


def test_risky_profiles_miss_more_submissions_than_normal_ones():
    def missing_rate(profile):
        expected, graded = _grades_for(profile, n_students=40)
        gradable = expected["lab"] + expected["control"]
        return (gradable - graded["lab"] - graded["control"]) / gradable

    assert missing_rate("expulsion_risk") > 2 * missing_rate("normal")


def test_groups_carry_the_cohorts_current_course_year():
    groups = generate_groups([{"id": 1, "name": "X"}])

    assert {g["course_year"] for g in groups} == {config.COHORT_CURRENT_COURSE_YEAR}
