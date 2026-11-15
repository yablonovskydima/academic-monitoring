from insights_service.insights.headlines import RiskDraft, compose_headline
from insights_service.insights.reasons import ReasonDraft
from insights_service.models.enums import (
    IndexCategory, ReasonDirection, ReasonStrength, RiskKind, RiskLevel, RiskType, Theme,
)


def reason(theme: Theme, title: str, text: str = "x", direction: ReasonDirection = ReasonDirection.risk) -> ReasonDraft:
    return ReasonDraft(theme, title, direction, ReasonStrength.main, text, None, "f", 1.0, None)


def risk(risk_type: RiskType, level: RiskLevel, *reasons: ReasonDraft) -> RiskDraft:
    kind = RiskKind.status if risk_type is RiskType.exam_admission_denial else RiskKind.forecast
    return RiskDraft(risk_type, kind, level, 0.5, list(reasons))


ATTENDANCE = reason(Theme.attendance, "Attendance", "Lecture absences: 78% — admission threshold is 75%")
GRADES = reason(Theme.grades, "Grades")


def test_admission_denial_comes_first_and_quotes_the_rule():
    headline = compose_headline(IndexCategory.low, [GRADES], [
        risk(RiskType.expulsion, RiskLevel.high, GRADES),
        risk(RiskType.exam_admission_denial, RiskLevel.high, ATTENDANCE),
    ])

    assert headline.text == "Not admitted to exams. Lecture absences: 78% — admission threshold is 75%"
    assert headline.theme is Theme.attendance
    assert headline.needs_attention


def test_high_expulsion_risk_names_the_main_reason():
    headline = compose_headline(IndexCategory.medium, [], [
        risk(RiskType.academic_debt, RiskLevel.high, GRADES),
        risk(RiskType.expulsion, RiskLevel.high, ATTENDANCE),
    ])

    assert headline.text == "High risk of expulsion. Main reason: attendance"
    assert headline.theme is Theme.attendance


def test_high_debt_risk():
    headline = compose_headline(IndexCategory.high, [], [risk(RiskType.academic_debt, RiskLevel.high, GRADES)])

    assert headline.text == "High risk of academic debt. Main reason: grades"


def test_protective_reasons_are_never_named_as_the_cause():
    protective = reason(Theme.grades, "Grades", direction=ReasonDirection.protective)

    headline = compose_headline(IndexCategory.low, [protective, ATTENDANCE], [])

    assert headline.text == "Low academic index. Main reason: attendance"


def test_moderate_concerns_are_listed():
    headline = compose_headline(IndexCategory.medium, [], [
        risk(RiskType.expulsion, RiskLevel.moderate),
        risk(RiskType.exam_admission_denial, RiskLevel.moderate),
    ])

    assert headline.text == (
        "Needs attention: close to the exam admission threshold, "
        "moderate risk of expulsion, medium academic index"
    )
    assert not headline.needs_attention


def test_no_concerns():
    headline = compose_headline(IndexCategory.high, [], [risk(RiskType.expulsion, RiskLevel.low)])

    assert headline.text == "No significant risks"
    assert headline.theme is None
    assert not headline.needs_attention
