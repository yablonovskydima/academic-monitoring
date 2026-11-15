import pytest
from pydantic import ValidationError

from insight_factories import forecast, prediction

from insights_service.models.enums import IndexCategory
from insights_service.schemas.prediction_input import InsightRunCreate
from insights_service.services.insight_run_service import InsightRunService
from insights_service.services.student_insight_service import StudentInsightService


def run(db, *predictions):
    return InsightRunService(db).process_run(InsightRunCreate(predictions=list(predictions)))


def test_a_student_in_the_latest_run_is_current(db_session):
    run(db_session, prediction(1))
    latest = run(db_session, prediction(1))

    insight = StudentInsightService(db_session).get_latest(1)

    assert insight.run_id == latest.id
    assert insight.is_current


def test_a_student_who_left_keeps_the_last_known_insight_marked_as_not_current(db_session):
    first = run(db_session, prediction(1), prediction(2))
    run(db_session, prediction(1))

    insight = StudentInsightService(db_session).get_latest(2)

    assert insight.run_id == first.id
    assert not insight.is_current


def test_history_marks_only_the_latest_run_as_current(db_session):
    run(db_session, prediction(1, index_category=IndexCategory.high))
    run(db_session, prediction(1, index_category=IndexCategory.low))

    history = StudentInsightService(db_session).get_history(1)

    assert [(h.index_category, h.is_current) for h in history] == [
        (IndexCategory.low, True),
        (IndexCategory.high, False),
    ]


def test_history_of_a_student_who_left_has_no_current_entry(db_session):
    run(db_session, prediction(1), prediction(2))
    run(db_session, prediction(1))

    assert [h.is_current for h in StudentInsightService(db_session).get_history(2)] == [False]


def test_the_list_lookup_only_returns_current_insights(db_session):
    run(db_session, prediction(1), prediction(2))
    run(db_session, prediction(1))

    current = StudentInsightService(db_session).search_current(student_ids=[1, 2])

    assert [(i.student_id, i.is_current) for i in current.items] == [(1, True)]


def test_forecasts_are_stored_and_returned_in_horizon_order(db_session):
    run(db_session, prediction(1, forecasts=[forecast(3, 51.0), forecast(2, 58.5)]))

    insight = StudentInsightService(db_session).get_latest(1)

    assert [(f.semesters_ahead, f.predicted_index_value) for f in insight.forecasts] == [(2, 58.5), (3, 51.0)]


def test_a_student_without_forecasts_gets_an_empty_list(db_session):
    run(db_session, prediction(1))

    assert StudentInsightService(db_session).get_latest(1).forecasts == []


def test_forecasts_belong_to_their_run(db_session):
    run(db_session, prediction(1, forecasts=[forecast(2, 40.0)]))
    run(db_session, prediction(1, forecasts=[forecast(2, 60.0)]))

    assert StudentInsightService(db_session).get_latest(1).forecasts[0].predicted_index_value == 60.0


def test_two_forecasts_for_one_horizon_are_rejected():
    with pytest.raises(ValidationError):
        prediction(1, forecasts=[forecast(2, 40.0), forecast(2, 41.0)])


def test_a_forecast_must_look_ahead():
    with pytest.raises(ValidationError):
        forecast(0, 40.0)
