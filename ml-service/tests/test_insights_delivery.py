from types import SimpleNamespace

import httpx
import pytest

from factories import make_features

import ml_service.clients.insights_service_client as client_module
from ml_service.clients.insights_service_client import ATTEMPTS, InsightsDeliveryError, InsightsServiceClient
from ml_service.ml.inference.insights_delivery import deliver_to_insights
from ml_service.ml.inference.insights_payload import InsightsPayloadBuilder
from ml_service.models.student_index import IndexCategory


class FakePost:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def __call__(self, url, json=None, timeout=None):
        self.calls.append((url, json))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return httpx.Response(outcome[0], json=outcome[1], request=httpx.Request("POST", url))


@pytest.fixture()
def sleeps():
    return []


def client(monkeypatch, sleeps, *outcomes) -> tuple[InsightsServiceClient, FakePost]:
    post = FakePost(*outcomes)
    monkeypatch.setattr(client_module.httpx, "post", post)
    return InsightsServiceClient("http://insights.test", sleep=sleeps.append), post


def test_a_new_run_is_posted_once(monkeypatch, sleeps):
    insights, post = client(monkeypatch, sleeps, (201, {"id": 5}))

    assert insights.submit_run({"x": 1}) == {"id": 5}
    assert post.calls == [("http://insights.test/insight-runs/", {"x": 1})]
    assert sleeps == []


def test_an_already_stored_run_counts_as_delivered(monkeypatch, sleeps):
    insights, _ = client(monkeypatch, sleeps, (200, {"id": 5}))

    assert insights.submit_run({})["id"] == 5


def test_network_errors_and_server_errors_are_retried(monkeypatch, sleeps):
    insights, post = client(monkeypatch, sleeps, httpx.ConnectError("refused"), (503, {}), (201, {"id": 7}))

    assert insights.submit_run({})["id"] == 7
    assert len(post.calls) == 3
    assert sleeps == [2, 4]


def test_a_rejected_run_is_not_retried(monkeypatch, sleeps):
    insights, post = client(monkeypatch, sleeps, (422, {"detail": "bad"}))

    with pytest.raises(InsightsDeliveryError, match="rejected the run: 422"):
        insights.submit_run({})
    assert len(post.calls) == 1


def test_giving_up_after_the_last_attempt(monkeypatch, sleeps):
    insights, post = client(monkeypatch, sleeps, *[httpx.ConnectError("refused")] * ATTEMPTS)

    with pytest.raises(InsightsDeliveryError, match=f"unreachable after {ATTEMPTS} attempts"):
        insights.submit_run({})
    assert len(post.calls) == ATTEMPTS


def builder_with_one_student() -> InsightsPayloadBuilder:
    builder = InsightsPayloadBuilder()
    builder.add_index(make_features(student_id=1), SimpleNamespace(id=1, index_value=70.0, category=IndexCategory.high), [])
    return builder


class FakeImport:
    def __init__(self, groups=None, error=None):
        self.groups = groups or {1: 10}
        self.error = error

    def get_student_groups(self):
        if self.error:
            raise self.error
        return self.groups


class FakeInsights:
    def __init__(self, error=None):
        self.error = error
        self.payloads = []

    def submit_run(self, payload):
        if self.error:
            raise self.error
        self.payloads.append(payload)
        return {"id": 42}


def test_delivery_sends_the_run_and_reports_the_insight_run_id():
    insights = FakeInsights()

    outcome = deliver_to_insights(builder_with_one_student(), 9, FakeImport(), insights)

    assert outcome == {"delivered": True, "insight_run_id": 42}
    assert insights.payloads[0]["source_job_id"] == 9
    assert insights.payloads[0]["predictions"][0]["group_id"] == 10


def test_delivery_is_skipped_when_insights_is_not_configured():
    assert deliver_to_insights(builder_with_one_student(), 9, FakeImport(), None) == {
        "delivered": False, "reason": "INSIGHTS_SERVICE_URL is not set",
    }


def test_delivery_is_skipped_when_nobody_was_scored():
    insights = FakeInsights()

    assert deliver_to_insights(InsightsPayloadBuilder(), 9, FakeImport(), insights)["delivered"] is False
    assert insights.payloads == []


@pytest.mark.parametrize("import_client,insights_client,reason", [
    (FakeImport(), FakeInsights(InsightsDeliveryError("down")), "InsightsDeliveryError: down"),
    (FakeImport(error=httpx.ConnectError("refused")), FakeInsights(), "ConnectError: refused"),
    (FakeImport(groups={2: 20}), FakeInsights(), "ValueError: import-service has no group"),
])
def test_a_failed_delivery_is_reported_instead_of_failing_the_inference(import_client, insights_client, reason):
    outcome = deliver_to_insights(builder_with_one_student(), 9, import_client, insights_client)

    assert outcome["delivered"] is False
    assert outcome["reason"].startswith(reason)
