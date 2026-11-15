import pytest

from insight_factories import TYPICAL_FEATURES

from insights_service.insights.reasons import ReasonDraft
from insights_service.insights.risk_levels import assess_admission, forecast_level, supported_level
from insights_service.models.enums import ReasonDirection, ReasonStrength, RiskLevel, Theme


def _reason(direction: ReasonDirection) -> ReasonDraft:
    return ReasonDraft(Theme.attendance, "Attendance", direction, ReasonStrength.main, "x", None, "f", 1.0, None)


@pytest.mark.parametrize("probability,level", [
    (0.0, RiskLevel.low),
    (0.34, RiskLevel.low),
    (0.35, RiskLevel.moderate),
    (0.64, RiskLevel.moderate),
    (0.65, RiskLevel.high),
    (1.0, RiskLevel.high),
])
def test_forecast_level_thresholds(probability, level):
    assert forecast_level(probability) is level


def test_an_elevated_level_needs_at_least_one_risk_reason():
    assert supported_level(0.9, [_reason(ReasonDirection.risk)]) is RiskLevel.high
    assert supported_level(0.5, [_reason(ReasonDirection.protective), _reason(ReasonDirection.risk)]) is RiskLevel.moderate
    assert supported_level(0.9, [_reason(ReasonDirection.protective)]) is RiskLevel.low
    assert supported_level(0.9, []) is RiskLevel.low
    assert supported_level(0.1, [_reason(ReasonDirection.risk)]) is RiskLevel.low


def test_admission_denied_by_lecture_absence_is_explained_by_the_rule():
    level, reasons = assess_admission({**TYPICAL_FEATURES, "lecture_absence_percent": 78.0})

    assert level is RiskLevel.high
    assert [r.text for r in reasons] == ["Lecture absences: 78% — admission threshold is 75%"]
    assert reasons[0].theme is Theme.attendance
    assert reasons[0].strength is ReasonStrength.main


def test_admission_denied_by_grade():
    level, reasons = assess_admission({**TYPICAL_FEATURES, "avg_grade": 47.4})

    assert level is RiskLevel.high
    assert reasons[0].text == "Semester average grade: 47.4 — minimum for admission is 50"
    assert reasons[0].theme is Theme.grades


def test_every_broken_rule_is_listed():
    level, reasons = assess_admission({
        **TYPICAL_FEATURES, "lecture_absence_percent": 80.0, "lab_absence_percent": 76.0, "avg_grade": 40.0,
    })

    assert level is RiskLevel.high
    assert [r.feature_name for r in reasons] == ["lecture_absence_percent", "lab_absence_percent", "avg_grade"]


def test_close_to_the_threshold_is_a_warning():
    level, reasons = assess_admission({**TYPICAL_FEATURES, "lab_absence_percent": 68.0, "avg_grade": 52.5})

    assert level is RiskLevel.moderate
    assert [r.text for r in reasons] == [
        "Lab absences: 68% — 7 p.p. below the admission threshold (75%)",
        "Semester average grade: 52.5 — only 2.5 above the minimum for admission (50)",
    ]
    assert all(r.strength is ReasonStrength.significant for r in reasons)


def test_a_breach_outranks_a_warning():
    level, reasons = assess_admission({**TYPICAL_FEATURES, "lecture_absence_percent": 90.0, "avg_grade": 52.0})

    assert level is RiskLevel.high
    assert [r.feature_name for r in reasons] == ["lecture_absence_percent"]


def test_nothing_critical_is_low_without_reasons():
    assert assess_admission(TYPICAL_FEATURES) == (RiskLevel.low, [])


def test_admission_rule_only_applies_to_full_time_students():
    assert assess_admission({**TYPICAL_FEATURES, "study_mode": "part_time", "avg_grade": 10.0}) == (RiskLevel.low, [])


def test_missing_features_mean_the_rule_cannot_be_checked():
    features = {k: v for k, v in TYPICAL_FEATURES.items() if k != "lab_absence_percent"}

    assert assess_admission(features) is None
