import pytest
from fastapi.testclient import TestClient

from insight_factories import contribution, forecast, prediction, risk

from insights_service.database import get_db
from insights_service.main import app
from insights_service.models.enums import IndexCategory, RiskType
from insights_service.schemas.prediction_input import InsightRunCreate
from insights_service.services.insight_run_service import InsightRunService


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def run(db_session):
    def _run(*predictions):
        return InsightRunService(db_session).process_run(InsightRunCreate(predictions=list(predictions)))
    return _run


def at_risk(student_id: int, group_id: int, index_value: float = 30.0):
    return prediction(
        student_id,
        group_id=group_id,
        index_category=IndexCategory.low,
        index_value=index_value,
        index_contributions=[contribution("lab_absence_percent", 60.0, -8.0)],
        risks=[risk(RiskType.expulsion, 0.9, contribution("lab_absence_percent", 60.0, 1.5))],
        forecasts=[forecast(2, index_value - 5)],
        lab_absence_percent=60.0,
    )


def test_current_list_is_scoped_to_the_given_groups_and_says_which_run(client, run):
    latest = run(prediction(1, group_id=10, index_value=80.0), at_risk(2, 10), prediction(3, group_id=20))

    body = client.get("/student-insights/current", params={"group_ids": [10]}).json()

    assert body["run"]["id"] == latest.id
    assert body["run"]["created_at"]
    assert body["total"] == 2
    assert [i["student_id"] for i in body["items"]] == [2, 1]


def test_current_list_items_are_light(client, run):
    run(at_risk(2, 10))

    [item] = client.get("/student-insights/current").json()["items"]

    assert item["headline"] == "High risk of expulsion. Main reason: attendance"
    assert item["is_current"] is True
    assert item["risks"] == [{"risk_type": "expulsion", "kind": "forecast", "level": "high"}]
    assert "index_reasons" not in item
    assert "forecasts" not in item


def test_current_list_filters_by_students_and_combines_with_groups(client, run):
    run(prediction(1, group_id=10), prediction(2, group_id=10), prediction(3, group_id=20))

    by_students = client.get("/student-insights/current", params={"student_ids": [1, 3]}).json()
    both = client.get("/student-insights/current", params={"student_ids": [1, 3], "group_ids": [10]}).json()

    assert sorted(i["student_id"] for i in by_students["items"]) == [1, 3]
    assert [i["student_id"] for i in both["items"]] == [1]


def test_current_list_is_paginated(client, run):
    run(*[prediction(i, index_value=50.0 + i) for i in range(1, 6)])

    page = client.get("/student-insights/current", params={"limit": 2, "offset": 2}).json()

    assert page["total"] == 5
    assert [i["student_id"] for i in page["items"]] == [3, 4]


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 501}, {"offset": -1}])
def test_current_list_rejects_bad_paging(client, params):
    assert client.get("/student-insights/current", params=params).status_code == 422


def test_current_list_before_any_run(client):
    assert client.get("/student-insights/current").json() == {"run": None, "total": 0, "items": []}


def test_student_card_has_reasons_risks_and_forecasts(client, run):
    run(at_risk(2, 10))

    card = client.get("/student-insights/2").json()

    assert card["is_current"] is True
    assert card["index_reasons"][0]["title"] == "Attendance"
    assert card["risks"][0]["reasons"][0]["text"].startswith("Lab absences: 60%")
    assert card["forecasts"] == [{"semesters_ahead": 2, "predicted_index_value": 25.0}]


def test_card_of_a_student_who_left_is_marked_not_current(client, run):
    run(prediction(1), prediction(2))
    run(prediction(1))

    assert client.get("/student-insights/2").json()["is_current"] is False
    assert client.get("/student-insights/999").status_code == 404


def test_history_and_changes_of_a_student(client, run):
    run(prediction(1, index_category=IndexCategory.high))
    run(prediction(1, index_category=IndexCategory.low))

    history = client.get("/student-insights/1/history", params={"limit": 1}).json()
    changes = client.get("/student-insights/1/changes").json()

    assert [(h["index_category"], h["is_current"]) for h in history] == [("low", True)]
    assert [c["text"] for c in changes] == ["Academic index: high → low"]


def test_latest_changes_filtered_to_worsened_and_groups(client, run):
    run(prediction(1, group_id=10, index_category=IndexCategory.high),
        prediction(2, group_id=10, index_category=IndexCategory.low),
        prediction(3, group_id=20, index_category=IndexCategory.high))
    latest = run(prediction(1, group_id=10, index_category=IndexCategory.medium),
                 prediction(2, group_id=10, index_category=IndexCategory.medium),
                 prediction(3, group_id=20, index_category=IndexCategory.low))

    body = client.get("/insight-changes/latest", params={"worsened_only": True, "group_ids": [10]}).json()

    assert body["run"]["id"] == latest.id
    assert [(c["student_id"], c["direction"]) for c in body["items"]] == [(1, "worsened")]


def test_latest_group_summaries_for_the_callers_groups(client, run):
    latest = run(at_risk(1, 10), prediction(2, group_id=10), prediction(3, group_id=20))

    body = client.get("/group-summaries/latest", params={"group_ids": [10]}).json()

    assert body["run"]["id"] == latest.id
    [summary] = body["items"]
    assert (summary["group_id"], summary["students_count"], summary["attention_count"]) == (10, 2, 1)
    assert summary["top_theme"] == "attendance"


def test_changes_and_summaries_before_any_run(client):
    assert client.get("/insight-changes/latest").json() == {"run": None, "items": []}
    assert client.get("/group-summaries/latest").json() == {"run": None, "items": []}
