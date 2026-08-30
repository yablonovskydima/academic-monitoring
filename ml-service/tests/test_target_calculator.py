from factories import make_features

from ml_service.ml.targets.target_calculator import TargetCalculator


def test_disappeared_next_semester_gives_zero_target():
    calc = TargetCalculator()
    features = make_features(disappeared_next_semester=True, avg_grade=95.0)

    assert calc.calculate_target(features) == 0.0


def test_repeated_subjects_caps_the_score():
    calc = TargetCalculator()
    features = make_features(
        avg_grade=100.0, grade_stddev=0.0,
        lecture_absence_percent=0.0, lab_absence_percent=0.0,
        unworked_absences_count=0, missing_submissions_count=0, late_submissions_count=0,
        repeated_subjects_count=1,
    )

    assert calc.calculate_target(features) == calc.REPEATED_SUBJECT_CAP


def test_critical_absence_caps_the_score_for_full_time_students():
    calc = TargetCalculator()
    features = make_features(
        avg_grade=100.0, grade_stddev=0.0,
        study_mode="full_time",
        lecture_absence_percent=80.0, lab_absence_percent=0.0,
        unworked_absences_count=0, missing_submissions_count=0, late_submissions_count=0,
    )

    assert calc.calculate_target(features) == calc.CRITICAL_ABSENCE_CAP


def test_critical_absence_does_not_cap_part_time_students():
    calc = TargetCalculator()
    features = make_features(
        avg_grade=100.0, grade_stddev=0.0,
        study_mode="part_time",
        lecture_absence_percent=80.0, lab_absence_percent=0.0,
        unworked_absences_count=0, missing_submissions_count=0, late_submissions_count=0,
    )

    # base score (100*0.5 - 80*0.1 = 42.0) is left uncapped for part-time students,
    # unlike the equivalent full-time case which gets capped to CRITICAL_ABSENCE_CAP
    assert calc.calculate_target(features) == 42.0


def test_admission_denial_triggers_on_critical_absence():
    calc = TargetCalculator()
    features = make_features(
        study_mode="full_time", lecture_absence_percent=75.0, lab_absence_percent=0.0, avg_grade=90.0,
    )

    assert calc.calculate_admission_denial_label(features) == 1


def test_admission_denial_triggers_on_low_grade():
    calc = TargetCalculator()
    features = make_features(
        study_mode="full_time", lecture_absence_percent=0.0, lab_absence_percent=0.0, avg_grade=49.9,
    )

    assert calc.calculate_admission_denial_label(features) == 1


def test_admission_denial_never_applies_to_part_time_students():
    calc = TargetCalculator()
    features = make_features(
        study_mode="part_time", lecture_absence_percent=100.0, avg_grade=0.0,
    )

    assert calc.calculate_admission_denial_label(features) == 0


def test_admission_denial_is_zero_when_nothing_critical():
    calc = TargetCalculator()
    features = make_features(
        study_mode="full_time", lecture_absence_percent=10.0, lab_absence_percent=10.0, avg_grade=80.0,
    )

    assert calc.calculate_admission_denial_label(features) == 0


def test_debt_label_reflects_repeated_subjects():
    calc = TargetCalculator()

    assert calc.calculate_debt_label(make_features(repeated_subjects_count=0)) == 0
    assert calc.calculate_debt_label(make_features(repeated_subjects_count=2)) == 1


def test_expulsion_label_reflects_disappearance():
    calc = TargetCalculator()

    assert calc.calculate_expulsion_label(make_features(disappeared_next_semester=False)) == 0
    assert calc.calculate_expulsion_label(make_features(disappeared_next_semester=True)) == 1


def test_build_horizon_dataset_uses_the_future_semesters_target_not_the_current_one():
    calc = TargetCalculator()

    current = make_features(
        student_id=1, semester_id=1,
        avg_grade=30.0, grade_stddev=0.0, lecture_absence_percent=0.0, lab_absence_percent=0.0,
        unworked_absences_count=0, missing_submissions_count=0, late_submissions_count=0,
    )
    future = make_features(
        student_id=1, semester_id=2,
        avg_grade=100.0, grade_stddev=0.0, lecture_absence_percent=0.0, lab_absence_percent=0.0,
        unworked_absences_count=0, missing_submissions_count=0, late_submissions_count=0,
    )

    X, y = calc.build_horizon_dataset([current, future], [1, 2], horizon=1)

    assert len(X) == 1
    assert X[0].semester_id == 1
    # target must come from the FUTURE row (avg_grade 100 -> 50.0), not the current one (30 -> 15.0)
    assert y[0] == 50.0


def test_build_horizon_dataset_skips_rows_with_no_future_semester():
    calc = TargetCalculator()
    only_semester = make_features(student_id=1, semester_id=1)

    X, y = calc.build_horizon_dataset([only_semester], [1, 2], horizon=1)

    assert X == []
    assert y == []


def test_build_classification_dataset_excludes_each_students_last_semester_when_required():
    calc = TargetCalculator()

    rows = [
        make_features(student_id=1, semester_id=1),
        make_features(student_id=1, semester_id=2),
        make_features(student_id=2, semester_id=1),
    ]

    X, _ = calc.build_classification_dataset(
        rows, [1, 2], calc.calculate_debt_label, requires_next_semester=True,
    )

    kept = {(f.student_id, f.semester_id) for f in X}
    assert kept == {(1, 1)}  # student 1's semester 2 (last) and student 2's semester 1 (last) dropped


def test_build_classification_dataset_keeps_last_semester_when_not_required():
    calc = TargetCalculator()

    rows = [
        make_features(student_id=1, semester_id=1),
        make_features(student_id=1, semester_id=2),
    ]

    X, _ = calc.build_classification_dataset(
        rows, [1, 2], calc.calculate_expulsion_label, requires_next_semester=False,
    )

    assert len(X) == 2
