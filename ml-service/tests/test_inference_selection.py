from factories import make_features

from ml_service.ml.inference.inference_service import current_semester_rows


def test_only_students_enrolled_in_the_latest_semester_are_scored():
    rows = [
        make_features(student_id=1, semester_id=1),
        make_features(student_id=1, semester_id=2),
        make_features(student_id=1, semester_id=3),
        make_features(student_id=2, semester_id=1),
        make_features(student_id=2, semester_id=2),
        make_features(student_id=3, semester_id=3),
    ]

    selected = current_semester_rows(rows)

    assert {(f.student_id, f.semester_id) for f in selected} == {(1, 3), (3, 3)}


def test_one_row_per_student():
    rows = [make_features(student_id=s, semester_id=sem) for s in (1, 2) for sem in (1, 2)]

    assert sorted(f.student_id for f in current_semester_rows(rows)) == [1, 2]
