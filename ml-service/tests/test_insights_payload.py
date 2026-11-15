import json
from types import SimpleNamespace

import pandas as pd
import pytest

from factories import make_features

from ml_service.ml.inference.insights_payload import InsightsPayloadBuilder
from ml_service.ml.inference.shap_contributions import all_contributions
from ml_service.models.student_index import IndexCategory


def index_row(id: int, value: float = 64.5, category: IndexCategory = IndexCategory.medium):
    return SimpleNamespace(id=id, index_value=value, category=category)


def filled_builder() -> InsightsPayloadBuilder:
    builder = InsightsPayloadBuilder()
    contributions = [{"feature_name": "avg_grade", "feature_value": 55.0, "shap_value": -3.0}]
    builder.add_index(make_features(student_id=1, semester_id=6), index_row(101), contributions)
    builder.add_index(make_features(student_id=2, semester_id=6), index_row(102, 80.0, IndexCategory.high), [])
    builder.add_risk(1, "expulsion", 0.7, contributions)
    builder.add_forecast(1, 2, 58.0)
    return builder


def test_all_contributions_keeps_every_feature():
    row = pd.Series({f"f{i}": float(i) for i in range(20)})

    contributions = all_contributions(row, [0.1 * i for i in range(20)])

    assert len(contributions) == 20
    assert contributions[3] == {"feature_name": "f3", "feature_value": 3.0, "shap_value": pytest.approx(0.3)}


def test_build_assembles_one_prediction_per_student_with_its_group():
    payload = filled_builder().build(inference_job_id=9, group_by_student={1: 10, 2: 20})

    assert payload["source_job_id"] == 9
    first, second = payload["predictions"]
    assert (first["student_id"], first["group_id"], first["student_index_id"]) == (1, 10, 101)
    assert first["index_category"] == "medium"
    assert first["risks"] == [{"risk_type": "expulsion", "probability": 0.7, "contributions": first["index_contributions"]}]
    assert first["forecasts"] == [{"semesters_ahead": 2, "predicted_index_value": 58.0}]
    assert first["features"]["study_mode"] == "full_time"
    assert (second["group_id"], second["risks"], second["forecasts"]) == (20, [], [])


def test_build_is_json_serializable():
    json.dumps(filled_builder().build(9, {1: 10, 2: 20}))


def test_a_scored_student_without_a_group_stops_the_build():
    with pytest.raises(ValueError, match="no group for 1 scored students"):
        filled_builder().build(9, {1: 10})


def test_payload_matches_the_insights_service_contract():
    insights_schema = pytest.importorskip("insights_service.schemas.prediction_input")

    run = insights_schema.InsightRunCreate.model_validate(filled_builder().build(9, {1: 10, 2: 20}))

    assert run.source_job_id == 9
    assert [p.student_id for p in run.predictions] == [1, 2]
    assert run.predictions[0].forecasts[0].semesters_ahead == 2
