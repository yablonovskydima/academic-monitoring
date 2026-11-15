from insights_service.insights.changes import StudentState, detect_changes
from insights_service.models.enums import ChangeDirection, ChangeKind, IndexCategory, RiskLevel, RiskType


def state(index: IndexCategory = IndexCategory.high, **levels: RiskLevel) -> StudentState:
    return StudentState(index, {RiskType(name): level for name, level in levels.items()})


def test_no_change_no_records():
    same = state(expulsion=RiskLevel.low)

    assert detect_changes(same, same) == []


def test_index_dropping_a_category_is_worsened():
    [change] = detect_changes(state(IndexCategory.high), state(IndexCategory.medium))

    assert change.kind is ChangeKind.index_category
    assert change.direction is ChangeDirection.worsened
    assert (change.from_value, change.to_value) == ("high", "medium")
    assert change.text == "Academic index: high → medium"


def test_risk_going_down_is_improved():
    [change] = detect_changes(state(expulsion=RiskLevel.high), state(expulsion=RiskLevel.moderate))

    assert change.kind is ChangeKind.risk_level
    assert change.risk_type is RiskType.expulsion
    assert change.direction is ChangeDirection.improved
    assert change.text == "Risk of expulsion: high → moderate"


def test_admission_changes_use_status_wording():
    [change] = detect_changes(
        state(exam_admission_denial=RiskLevel.low), state(exam_admission_denial=RiskLevel.high),
    )

    assert change.direction is ChangeDirection.worsened
    assert change.text == "Exam admission: admitted → not admitted"


def test_a_risk_missing_from_either_run_is_not_a_change():
    assert detect_changes(state(expulsion=RiskLevel.low), state(academic_debt=RiskLevel.high)) == []


def test_several_changes_at_once():
    changes = detect_changes(
        state(IndexCategory.medium, expulsion=RiskLevel.low, academic_debt=RiskLevel.high),
        state(IndexCategory.low, expulsion=RiskLevel.high, academic_debt=RiskLevel.high),
    )

    assert [(c.kind, c.risk_type) for c in changes] == [
        (ChangeKind.index_category, None),
        (ChangeKind.risk_level, RiskType.expulsion),
    ]
