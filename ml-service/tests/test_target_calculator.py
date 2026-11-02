import pytest

from factories import make_features

from ml_service.ml.targets.target_calculator import LabelWindow, TargetCalculator

SPOTLESS = dict(
    avg_grade=100.0, grade_stddev=0.0,
    lecture_absence_percent=0.0, lab_absence_percent=0.0,
    unworked_absences_count=0, missing_submissions_count=0, late_submissions_count=0,
)


def test_spotless_semester_scores_100():
    assert TargetCalculator().calculate_target(make_features(**SPOTLESS)) == 100.0


def test_hopeless_semester_scores_0():
    features = make_features(
        study_mode="part_time",
        avg_grade=0.0, grade_stddev=60.0,
        lecture_absence_percent=100.0, lab_absence_percent=100.0,
        total_sessions=40, unworked_absences_count=40,
        total_gradable_sessions=20, missing_submissions_count=20, late_submissions_count=20,
    )

    assert TargetCalculator().calculate_target(features) == 0.0


def test_typical_semester_lands_in_the_upper_half_not_at_zero():
    features = make_features(
        avg_grade=75.0, grade_stddev=15.0,
        lecture_absence_percent=12.0, lab_absence_percent=12.0,
        total_sessions=126, unworked_absences_count=9,
        total_gradable_sessions=70, missing_submissions_count=2, late_submissions_count=8,
    )

    assert 70.0 <= TargetCalculator().calculate_target(features) <= 90.0


def test_penalties_are_rates_not_raw_counts():
    calc = TargetCalculator()
    light_load = make_features(**{**SPOTLESS, "total_gradable_sessions": 20, "late_submissions_count": 10})
    heavy_load = make_features(**{**SPOTLESS, "total_gradable_sessions": 100, "late_submissions_count": 10})

    assert calc.calculate_target(heavy_load) > calc.calculate_target(light_load)


def test_missing_submissions_lower_the_score():
    calc = TargetCalculator()

    assert (
        calc.calculate_target(make_features(**{**SPOTLESS, "missing_submissions_count": 10}))
        < calc.calculate_target(make_features(**SPOTLESS))
    )


def test_zero_totals_do_not_divide_by_zero():
    features = make_features(**{**SPOTLESS, "total_sessions": 0, "total_gradable_sessions": 0})

    assert TargetCalculator().calculate_target(features) == 100.0


def test_next_semester_outcomes_do_not_leak_into_the_semesters_own_score():
    calc = TargetCalculator()
    plain = make_features(**SPOTLESS)
    with_outcomes = make_features(**SPOTLESS, disappeared_next_semester=True, repeated_subjects_count=3)

    assert calc.calculate_target(with_outcomes) == calc.calculate_target(plain)


def test_critical_absence_caps_the_score_for_full_time_students():
    calc = TargetCalculator()
    features = make_features(**{**SPOTLESS, "study_mode": "full_time", "lecture_absence_percent": 80.0})

    assert calc.calculate_target(features) == calc.CRITICAL_ABSENCE_CAP


def test_critical_absence_does_not_cap_part_time_students():
    calc = TargetCalculator()
    features = make_features(**{**SPOTLESS, "study_mode": "part_time", "lecture_absence_percent": 80.0})

    assert calc.calculate_target(features) == 93.6


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


def test_build_horizon_dataset_uses_the_future_semesters_score_not_the_current_one():
    calc = TargetCalculator()
    current = make_features(student_id=1, semester_id=1, **{**SPOTLESS, "avg_grade": 30.0})
    future = make_features(student_id=1, semester_id=2, **SPOTLESS)

    X, y = calc.build_horizon_dataset([current, future], [1, 2], horizon=1)

    assert [f.semester_id for f in X] == [1]
    assert y == [100.0]


def test_build_horizon_dataset_gives_dropouts_the_dropped_out_target():
    calc = TargetCalculator()
    rows = [
        make_features(student_id=1, semester_id=1, disappeared_next_semester=True),
        make_features(student_id=2, semester_id=1),
        make_features(student_id=2, semester_id=2),
    ]

    X, y = calc.build_horizon_dataset(rows, [1, 2], horizon=1)

    by_student = {f.student_id: target for f, target in zip(X, y)}
    assert by_student[1] == calc.DROPPED_OUT_TARGET
    assert by_student[2] > calc.DROPPED_OUT_TARGET


def test_build_horizon_dataset_counts_a_dropout_for_every_horizon_past_the_last_semester():
    calc = TargetCalculator()
    rows = [
        make_features(student_id=1, semester_id=1),
        make_features(student_id=1, semester_id=2, disappeared_next_semester=True),
    ]

    X, y = calc.build_horizon_dataset(rows, [1, 2, 3, 4], horizon=2)

    assert [(f.semester_id, target) for f, target in zip(X, y)] == [(1, 0.0), (2, 0.0)]


def test_build_horizon_dataset_skips_a_gap_semester_the_student_came_back_from():
    calc = TargetCalculator()
    rows = [
        make_features(student_id=1, semester_id=1),
        make_features(student_id=1, semester_id=3),
    ]

    X, _ = calc.build_horizon_dataset(rows, [1, 2, 3], horizon=1)

    assert X == []


def test_build_horizon_dataset_skips_rows_whose_target_is_beyond_the_data():
    calc = TargetCalculator()

    X, y = calc.build_horizon_dataset([make_features(student_id=1, semester_id=2)], [1, 2], horizon=1)

    assert X == []
    assert y == []


def _three_students():
    return [
        make_features(student_id=1, semester_id=1),
        make_features(student_id=1, semester_id=2),
        make_features(student_id=2, semester_id=1, disappeared_next_semester=True),
    ]


def _kept(X):
    return {(f.student_id, f.semester_id) for f in X}


def test_current_semester_labels_keep_every_row():
    calc = TargetCalculator()

    X, _ = calc.build_classification_dataset(
        _three_students(), [1, 2], calc.calculate_admission_denial_label, LabelWindow.current_semester,
    )

    assert _kept(X) == {(1, 1), (1, 2), (2, 1)}


def test_next_semester_labels_drop_only_the_last_semester_and_keep_the_dropouts_positive_row():
    calc = TargetCalculator()

    X, y = calc.build_classification_dataset(
        _three_students(), [1, 2], calc.calculate_expulsion_label, LabelWindow.next_semester,
    )

    assert _kept(X) == {(1, 1), (2, 1)}
    assert sum(y) == 1


def test_next_semester_enrolled_labels_also_drop_rows_of_students_who_left():
    calc = TargetCalculator()

    X, _ = calc.build_classification_dataset(
        _three_students(), [1, 2], calc.calculate_debt_label, LabelWindow.next_semester_enrolled,
    )

    assert _kept(X) == {(1, 1)}


@pytest.mark.parametrize("window", list(LabelWindow))
def test_every_label_window_returns_aligned_features_and_labels(window):
    calc = TargetCalculator()

    X, y = calc.build_classification_dataset(_three_students(), [1, 2], calc.calculate_expulsion_label, window)

    assert len(X) == len(y)
