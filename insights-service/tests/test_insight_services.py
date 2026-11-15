import pytest
from pydantic import ValidationError

from insight_factories import contribution, prediction, risk

from insights_service.models.enums import (
    ChangeDirection, IndexCategory, InsightTarget, ReasonDirection, RiskKind, RiskLevel, RiskType, Theme,
)
from insights_service.schemas.prediction_input import InsightRunCreate
from insights_service.services.group_summary_service import GroupSummaryService
from insights_service.services.insight_change_service import InsightChangeService
from insights_service.services.insight_run_service import InsightRunService
from insights_service.services.student_insight_service import StudentInsightService


def cohort(n: int = 30, group_id: int = 1, start: int = 100) -> list:
    return [prediction(start + i, group_id=group_id, lab_absence_percent=float(i)) for i in range(n)]


def at_risk_student(student_id: int = 1, group_id: int = 1, expulsion: float = 0.8, **features):
    return prediction(
        student_id,
        group_id=group_id,
        index_category=IndexCategory.low,
        index_value=31.5,
        index_contributions=[
            contribution("lab_absence_percent", 60.0, -9.0),
            contribution("cumulative_absence_percent", 55.0, -3.0),
            contribution("avg_grade", 80.0, 2.0),
            contribution("course_year", 3, -4.0),
        ],
        risks=[
            risk(RiskType.expulsion, expulsion, contribution("lab_absence_percent", 60.0, 1.4)),
            risk(RiskType.academic_debt, 0.2, contribution("avg_grade", 80.0, -0.5)),
            risk(RiskType.exam_admission_denial, 0.9, contribution("lab_absence_percent", 60.0, 3.0)),
        ],
        lab_absence_percent=60.0,
        **features,
    )


def run(db, *predictions, source_job_id=None):
    return InsightRunService(db).process_run(InsightRunCreate(source_job_id=source_job_id, predictions=list(predictions)))


def test_a_run_stores_a_readable_insight_per_student(db_session):
    stored = run(db_session, at_risk_student(), *cohort())

    insight = StudentInsightService(db_session).get_latest(1)

    assert stored.students_count == 31
    assert insight.run_id == stored.id
    assert insight.student_index_id == 1001
    assert insight.headline == "High risk of expulsion. Main reason: attendance"

    index_reason = insight.index_reasons[0]
    assert index_reason.target is InsightTarget.index
    assert index_reason.theme is Theme.attendance
    assert index_reason.direction is ReasonDirection.risk
    assert index_reason.text == "Lab absences: 60% — higher than 97% of students"
    assert index_reason.percentile == 97
    assert index_reason.action is not None
    assert [r.rank for r in insight.index_reasons] == list(range(1, len(insight.index_reasons) + 1))
    assert all(r.theme is not Theme.context for r in insight.index_reasons)


def test_risks_carry_their_level_kind_and_own_reasons(db_session):
    run(db_session, at_risk_student(lecture_absence_percent=80.0), *cohort())

    risks = {r.risk_type: r for r in StudentInsightService(db_session).get_latest(1).risks}

    assert list(risks) == [RiskType.expulsion, RiskType.academic_debt, RiskType.exam_admission_denial]
    assert (risks[RiskType.expulsion].kind, risks[RiskType.expulsion].level) == (RiskKind.forecast, RiskLevel.high)
    assert risks[RiskType.academic_debt].level is RiskLevel.low
    assert risks[RiskType.academic_debt].reasons[0].direction is ReasonDirection.protective

    admission = risks[RiskType.exam_admission_denial]
    assert (admission.kind, admission.level) == (RiskKind.status, RiskLevel.high)
    assert admission.probability == 0.9
    assert [r.text for r in admission.reasons] == ["Lecture absences: 80% — admission threshold is 75%"]


def test_reasons_are_not_mixed_up_between_targets(db_session):
    run(db_session, at_risk_student(), *cohort())

    insight = StudentInsightService(db_session).get_latest(1)

    assert {r.target for r in insight.index_reasons} == {InsightTarget.index}
    for risk_insight in insight.risks:
        assert {r.target.value for r in risk_insight.reasons} <= {risk_insight.risk_type.value}


def test_admission_falls_back_to_the_model_when_the_rule_cannot_be_checked(db_session):
    student = prediction(
        1,
        risks=[risk(RiskType.exam_admission_denial, 0.9, contribution("lab_absence_percent", 80.0, 3.0))],
    )
    student.features.pop("lab_absence_percent")

    run(db_session, student)

    [admission] = StudentInsightService(db_session).get_latest(1).risks
    assert (admission.kind, admission.level) == (RiskKind.status, RiskLevel.high)
    assert admission.reasons[0].text == "Lab absences: 80%"


def test_the_first_run_has_no_changes_and_the_second_records_them(db_session):
    first = run(db_session, at_risk_student(expulsion=0.4), prediction(2))
    assert InsightChangeService(db_session).get_for_run(first.id) == []

    second = run(db_session, at_risk_student(expulsion=0.9), prediction(2))

    changes = InsightChangeService(db_session).get_for_run(second.id)
    assert [(c.student_id, c.risk_type, c.from_value, c.to_value, c.direction) for c in changes] == [
        (1, RiskType.expulsion, "moderate", "high", ChangeDirection.worsened),
    ]
    assert changes[0].previous_run_id == first.id
    assert changes[0].text == "Risk of expulsion: moderate → high"


def test_worsened_only_filter_and_per_student_history(db_session):
    run(db_session, prediction(1, index_category=IndexCategory.high), prediction(2, index_category=IndexCategory.low))
    run(db_session, prediction(1, index_category=IndexCategory.medium), prediction(2, index_category=IndexCategory.medium))

    service = InsightChangeService(db_session)

    assert {c.student_id for c in service.get_latest().items} == {1, 2}
    assert [c.student_id for c in service.get_latest(worsened_only=True).items] == [1]
    assert [c.text for c in service.get_for_student(2)] == ["Academic index: low → medium"]


def test_a_student_new_in_this_run_has_no_changes(db_session):
    run(db_session, prediction(1))
    second = run(db_session, prediction(1), at_risk_student(2))

    assert InsightChangeService(db_session).get_for_run(second.id) == []


def test_the_same_inference_job_is_processed_only_once(db_session):
    first = run(db_session, at_risk_student(), source_job_id=42)
    again = run(db_session, prediction(1), prediction(2), source_job_id=42)

    assert again.id == first.id
    assert again.students_count == 1
    assert len(StudentInsightService(db_session).get_history(1)) == 1
    assert StudentInsightService(db_session).get_latest(2) is None


def test_a_concurrent_duplicate_of_a_job_returns_the_run_that_won(db_session):
    winner = run(db_session, prediction(1), source_job_id=42)
    service = InsightRunService(db_session)
    real_lookup = service.runs.get_by_source_job_id
    lookups = iter([None])
    service.runs.get_by_source_job_id = lambda job_id: next(lookups, None) or real_lookup(job_id)

    loser = service.process_run(InsightRunCreate(source_job_id=42, predictions=[prediction(1), prediction(2)]))

    assert loser.id == winner.id
    assert InsightRunService(db_session).get_latest().id == winner.id


def test_group_summaries_count_risks_attention_and_worsening(db_session):
    run(db_session, prediction(1, group_id=10), prediction(2, group_id=10), prediction(3, group_id=20))
    latest = run(
        db_session,
        at_risk_student(1, group_id=10),
        at_risk_student(2, group_id=10, expulsion=0.1),
        prediction(3, group_id=20),
    )

    summaries = {s.group_id: s for s in GroupSummaryService(db_session).get_for_run(latest.id)}

    group = summaries[10]
    assert group.students_count == 2
    assert group.index_low_count == 2
    assert group.expulsion_high_count == 1
    assert group.attention_count == 2
    assert group.worsened_count == 2
    assert group.top_theme is Theme.attendance

    calm = summaries[20]
    assert (calm.attention_count, calm.worsened_count, calm.top_theme) == (0, 0, None)


def test_group_summaries_can_be_filtered_to_the_callers_groups(db_session):
    run(db_session, prediction(1, group_id=10), prediction(2, group_id=20), prediction(3, group_id=30))

    assert [s.group_id for s in GroupSummaryService(db_session).get_latest([10, 30]).items] == [10, 30]


def test_latest_insights_for_a_list_of_students_come_from_the_latest_run_only(db_session):
    run(db_session, prediction(1), prediction(2), prediction(3))
    latest = run(db_session, prediction(1), prediction(2))

    current = StudentInsightService(db_session).search_current(student_ids=[1, 2, 3, 99])

    assert sorted(i.student_id for i in current.items) == [1, 2]
    assert current.total == 2
    assert current.run.id == latest.id
    assert {i.run_id for i in current.items} == {latest.id}
    assert StudentInsightService(db_session).search_current(student_ids=[]).items == []


def test_history_is_newest_first(db_session):
    run(db_session, prediction(1, index_category=IndexCategory.high))
    run(db_session, prediction(1, index_category=IndexCategory.low))

    history = StudentInsightService(db_session).get_history(1)

    assert [h.index_category for h in history] == [IndexCategory.low, IndexCategory.high]


def test_reads_on_an_empty_database(db_session):
    assert InsightRunService(db_session).get_latest() is None
    assert StudentInsightService(db_session).get_latest(1) is None
    assert InsightChangeService(db_session).get_latest().model_dump() == {"run": None, "items": []}
    assert GroupSummaryService(db_session).get_latest().model_dump() == {"run": None, "items": []}
    assert StudentInsightService(db_session).search_current().model_dump() == {"run": None, "total": 0, "items": []}


def test_a_run_must_have_predictions_and_one_per_student():
    with pytest.raises(ValidationError):
        InsightRunCreate(predictions=[])
    with pytest.raises(ValidationError):
        InsightRunCreate(predictions=[prediction(1), prediction(1)])


def test_a_student_cannot_have_two_predictions_of_one_risk_type():
    with pytest.raises(ValidationError):
        prediction(1, risks=[risk(RiskType.expulsion, 0.1), risk(RiskType.expulsion, 0.2)])
