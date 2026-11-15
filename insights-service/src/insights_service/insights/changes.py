from dataclasses import dataclass

from insights_service.insights.feature_catalog import RISK_LABELS
from insights_service.models.enums import ChangeDirection, ChangeKind, IndexCategory, RiskLevel, RiskType

INDEX_SEVERITY = {IndexCategory.high: 0, IndexCategory.medium: 1, IndexCategory.low: 2}
LEVEL_SEVERITY = {RiskLevel.low: 0, RiskLevel.moderate: 1, RiskLevel.high: 2}

ADMISSION_LABELS = {RiskLevel.low: "admitted", RiskLevel.moderate: "near the threshold", RiskLevel.high: "not admitted"}


@dataclass(frozen=True)
class StudentState:
    index_category: IndexCategory
    risk_levels: dict[RiskType, RiskLevel]


@dataclass(frozen=True)
class ChangeDraft:
    kind: ChangeKind
    risk_type: RiskType | None
    from_value: str
    to_value: str
    direction: ChangeDirection
    text: str


def detect_changes(previous: StudentState, current: StudentState) -> list[ChangeDraft]:
    changes: list[ChangeDraft] = []

    if previous.index_category != current.index_category:
        changes.append(ChangeDraft(
            kind=ChangeKind.index_category,
            risk_type=None,
            from_value=previous.index_category.value,
            to_value=current.index_category.value,
            direction=_direction(INDEX_SEVERITY[previous.index_category], INDEX_SEVERITY[current.index_category]),
            text=f"Academic index: {previous.index_category.value} → {current.index_category.value}",
        ))

    for risk_type in RiskType:
        before = previous.risk_levels.get(risk_type)
        after = current.risk_levels.get(risk_type)
        if before is None or after is None or before == after:
            continue

        if risk_type is RiskType.exam_admission_denial:
            text = f"Exam admission: {ADMISSION_LABELS[before]} → {ADMISSION_LABELS[after]}"
        else:
            text = f"Risk of {RISK_LABELS[risk_type]}: {before.value} → {after.value}"

        changes.append(ChangeDraft(
            kind=ChangeKind.risk_level,
            risk_type=risk_type,
            from_value=before.value,
            to_value=after.value,
            direction=_direction(LEVEL_SEVERITY[before], LEVEL_SEVERITY[after]),
            text=text,
        ))

    return changes


def _direction(before: int, after: int) -> ChangeDirection:
    return ChangeDirection.worsened if after > before else ChangeDirection.improved
