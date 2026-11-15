from insight_factories import contribution

from insights_service.insights.cohort import Cohort
from insights_service.insights.reasons import build_reasons, describe_feature
from insights_service.models.enums import ReasonDirection, ReasonStrength, Theme

NO_COHORT = Cohort([])
LAB_COHORT = Cohort({"lab_absence_percent": float(v), "avg_grade": float(v)} for v in range(100))


def test_absence_features_are_one_attendance_reason_led_by_the_strongest():
    reasons = build_reasons(
        [
            contribution("absence_percent", 30, 0.4),
            contribution("lab_absence_percent", 40, 0.9),
            contribution("lecture_absence_percent", 20, 0.2),
            contribution("cumulative_absence_percent", 25, 0.3),
        ],
        NO_COHORT,
        higher_output_is_worse=True,
    )

    assert len(reasons) == 1
    assert reasons[0].theme is Theme.attendance
    assert reasons[0].title == "Attendance"
    assert reasons[0].feature_name == "lab_absence_percent"
    assert reasons[0].text == "Lab absences: 40%"


def test_for_the_index_a_negative_contribution_is_a_risk_factor():
    reasons = build_reasons(
        [contribution("absence_percent", 40, -6.0), contribution("avg_grade", 90, 3.0)],
        NO_COHORT,
        higher_output_is_worse=False,
    )

    by_theme = {r.theme: r for r in reasons}
    assert by_theme[Theme.attendance].direction is ReasonDirection.risk
    assert by_theme[Theme.grades].direction is ReasonDirection.protective


def test_for_a_risk_a_positive_contribution_is_a_risk_factor():
    reasons = build_reasons([contribution("avg_grade", 40, 1.2)], NO_COHORT, higher_output_is_worse=True)

    assert reasons[0].direction is ReasonDirection.risk


def test_context_and_unknown_features_are_never_reasons():
    reasons = build_reasons(
        [
            contribution("course_year", 3, 5.0),
            contribution("study_mode_full_time", 1, 4.0),
            contribution("brand_new_feature", 1, 9.0),
            contribution("avg_grade", 40, 0.5),
        ],
        NO_COHORT,
        higher_output_is_worse=True,
    )

    assert [r.theme for r in reasons] == [Theme.grades]
    assert reasons[0].strength is ReasonStrength.main


def test_strength_follows_the_share_of_the_total():
    reasons = build_reasons(
        [
            contribution("lab_absence_percent", 40, 6.0),
            contribution("avg_grade", 50, 3.0),
            contribution("late_submissions_count", 12, 1.5),
        ],
        NO_COHORT,
        higher_output_is_worse=True,
    )

    assert [r.strength for r in reasons] == [ReasonStrength.main, ReasonStrength.significant, ReasonStrength.minor]


def test_tiny_themes_are_dropped():
    reasons = build_reasons(
        [contribution("lab_absence_percent", 40, 10.0), contribution("avg_grade", 50, 0.5)],
        NO_COHORT,
        higher_output_is_worse=True,
    )

    assert [r.theme for r in reasons] == [Theme.attendance]


def test_the_number_of_reasons_is_capped():
    contributions = [
        contribution("lab_absence_percent", 40, 10.0),
        contribution("avg_grade", 50, 5.0),
        contribution("late_submissions_count", 12, 4.0),
        contribution("avg_grade_delta", -9, 3.0),
    ]

    assert len(build_reasons(contributions, NO_COHORT, True, max_reasons=2)) == 2
    assert len(build_reasons(contributions, NO_COHORT, True)) == 3


def test_value_is_compared_with_the_other_students():
    text, percentile = describe_feature("lab_absence_percent", 90.0, ReasonDirection.risk, LAB_COHORT)

    assert text == "Lab absences: 90% — higher than 90% of students"
    assert percentile == 90


def test_a_low_grade_is_worded_as_lower():
    text, percentile = describe_feature("avg_grade", 10.0, ReasonDirection.risk, LAB_COHORT)

    assert text == "Semester average grade: 10.0 — lower than 89% of students"
    assert percentile == 89


def test_protective_values_are_worded_the_other_way():
    text, _ = describe_feature("lab_absence_percent", 5.0, ReasonDirection.protective, LAB_COHORT)

    assert text == "Lab absences: 5% — lower than 94% of students"


def test_no_comparison_when_it_would_be_unflattering_to_the_claim_or_the_cohort_is_small():
    assert describe_feature("lab_absence_percent", 20.0, ReasonDirection.risk, LAB_COHORT) == (
        "Lab absences: 20%", None,
    )
    assert describe_feature("lab_absence_percent", 90.0, ReasonDirection.risk, Cohort([{"lab_absence_percent": 1.0}])) == (
        "Lab absences: 90%", None,
    )


def test_a_trend_reason_must_point_the_same_way_as_the_change():
    assert describe_feature("avg_grade_delta", -9.6, ReasonDirection.risk, NO_COHORT) == (
        "Average grade vs. last semester: -9.6", None,
    )
    assert describe_feature("avg_grade_delta", 9.6, ReasonDirection.risk, NO_COHORT) == (None, None)
    assert describe_feature("absence_percent_delta", 7.0, ReasonDirection.risk, NO_COHORT) == (
        "Absences vs. last semester: +7 p.p.", None,
    )


def test_a_trend_too_small_to_matter_is_not_a_reason():
    assert describe_feature("avg_grade_delta", 0.2, ReasonDirection.protective, NO_COHORT) == (None, None)
    assert describe_feature("absence_percent_delta", 4.0, ReasonDirection.risk, NO_COHORT) == (None, None)
    assert describe_feature("avg_grade_delta", 3.0, ReasonDirection.protective, NO_COHORT)[0] is not None


def test_an_inconsistent_trend_feature_gives_way_to_the_next_one():
    reasons = build_reasons(
        [contribution("avg_grade_delta", 9.6, 2.0), contribution("absence_percent_delta", 8.0, 1.0)],
        NO_COHORT,
        higher_output_is_worse=True,
    )

    assert reasons[0].feature_name == "absence_percent_delta"


def test_only_risk_reasons_carry_an_action():
    reasons = build_reasons(
        [contribution("lab_absence_percent", 40, 2.0), contribution("avg_grade", 90, -2.0)],
        NO_COHORT,
        higher_output_is_worse=True,
    )

    by_direction = {r.direction: r for r in reasons}
    assert by_direction[ReasonDirection.risk].action.startswith("Discuss the reasons for the absences")
    assert by_direction[ReasonDirection.protective].action is None


def test_no_contributions_no_reasons():
    assert build_reasons([], NO_COHORT, higher_output_is_worse=True) == []
