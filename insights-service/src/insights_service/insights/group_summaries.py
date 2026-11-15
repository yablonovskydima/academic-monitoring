from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from insights_service.insights.changes import StudentState
from insights_service.models.enums import IndexCategory, RiskLevel, RiskType, Theme


@dataclass(frozen=True)
class StudentOutcome:
    student_id: int
    group_id: int
    state: StudentState
    needs_attention: bool
    main_theme: Theme | None


@dataclass(frozen=True)
class GroupSummaryDraft:
    group_id: int
    students_count: int
    index_high_count: int
    index_medium_count: int
    index_low_count: int
    expulsion_high_count: int
    debt_high_count: int
    admission_denied_count: int
    attention_count: int
    worsened_count: int
    top_theme: Theme | None


def summarize_groups(outcomes: Iterable[StudentOutcome], worsened_student_ids: set[int]) -> list[GroupSummaryDraft]:
    by_group: dict[int, list[StudentOutcome]] = {}
    for outcome in outcomes:
        by_group.setdefault(outcome.group_id, []).append(outcome)

    return [_summarize(group_id, members, worsened_student_ids) for group_id, members in sorted(by_group.items())]


def _summarize(group_id: int, members: list[StudentOutcome], worsened_student_ids: set[int]) -> GroupSummaryDraft:
    def count_index(category: IndexCategory) -> int:
        return sum(1 for m in members if m.state.index_category is category)

    def count_high(risk_type: RiskType) -> int:
        return sum(1 for m in members if m.state.risk_levels.get(risk_type) is RiskLevel.high)

    themes = Counter(m.main_theme for m in members if m.needs_attention and m.main_theme is not None)
    theme_order = list(Theme)
    top_theme = min(themes, key=lambda theme: (-themes[theme], theme_order.index(theme))) if themes else None

    return GroupSummaryDraft(
        group_id=group_id,
        students_count=len(members),
        index_high_count=count_index(IndexCategory.high),
        index_medium_count=count_index(IndexCategory.medium),
        index_low_count=count_index(IndexCategory.low),
        expulsion_high_count=count_high(RiskType.expulsion),
        debt_high_count=count_high(RiskType.academic_debt),
        admission_denied_count=count_high(RiskType.exam_admission_denial),
        attention_count=sum(1 for m in members if m.needs_attention),
        worsened_count=sum(1 for m in members if m.student_id in worsened_student_ids),
        top_theme=top_theme,
    )
