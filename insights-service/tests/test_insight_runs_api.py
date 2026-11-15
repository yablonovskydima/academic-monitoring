import pytest
from fastapi.testclient import TestClient

from insight_factories import contribution, prediction, risk

from insights_service.database import get_db
from insights_service.main import app
from insights_service.models.enums import RiskType


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def body(*predictions, source_job_id=None) -> dict:
    payload = {"predictions": [p.model_dump(mode="json") for p in predictions]}
    if source_job_id is not None:
        payload["source_job_id"] = source_job_id
    return payload


def test_a_new_run_is_processed_and_returns_201(client):
    student = prediction(
        1, risks=[risk(RiskType.expulsion, 0.9, contribution("lab_absence_percent", 60.0, 1.5))],
    )

    response = client.post("/insight-runs/", json=body(student, prediction(2), source_job_id=7))

    assert response.status_code == 201
    assert response.json()["source_job_id"] == 7
    assert response.json()["students_count"] == 2
    assert response.json()["semester_id"] == 6


def test_the_same_job_again_returns_200_with_the_stored_run(client):
    first = client.post("/insight-runs/", json=body(prediction(1), source_job_id=7)).json()

    again = client.post("/insight-runs/", json=body(prediction(1), prediction(2), source_job_id=7))

    assert again.status_code == 200
    assert again.json() == first


def test_runs_without_a_job_id_are_never_deduplicated(client):
    first = client.post("/insight-runs/", json=body(prediction(1))).json()
    second = client.post("/insight-runs/", json=body(prediction(1))).json()

    assert second["id"] != first["id"]


@pytest.mark.parametrize("payload", [
    {"predictions": []},
    {},
    body(prediction(1), prediction(1)),
])
def test_invalid_runs_are_rejected_with_422(client, payload):
    assert client.post("/insight-runs/", json=payload).status_code == 422


def test_an_out_of_range_probability_is_rejected(client):
    payload = body(prediction(1))
    payload["predictions"][0]["risks"][0]["probability"] = 1.5

    assert client.post("/insight-runs/", json=payload).status_code == 422


def test_a_full_shap_vector_is_accepted(client):
    vector = [contribution(f"feature_{i}", float(i), 0.01 * i) for i in range(40)]
    student = prediction(1, index_contributions=vector, risks=[risk(RiskType.expulsion, 0.2, *vector)])

    assert client.post("/insight-runs/", json=body(student)).status_code == 201


def test_runs_can_be_read_back(client):
    created = client.post("/insight-runs/", json=body(prediction(1))).json()

    assert client.get(f"/insight-runs/{created['id']}").json() == created
    assert client.get("/insight-runs/latest").json() == created
    assert client.get("/insight-runs/999").status_code == 404


def test_latest_is_404_before_any_run(client):
    assert client.get("/insight-runs/latest").status_code == 404


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
