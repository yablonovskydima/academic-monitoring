import numpy as np
import pandas as pd

from ml_service.ml.inference.shap_contributions import background_sample, make_explainer, top_contributions
from ml_service.ml.training.index_trainer import IndexTrainer


def test_background_sample_is_deterministic_and_bounded():
    rows = list(range(1000))

    assert background_sample(rows) == background_sample(rows)
    assert len(background_sample(rows)) == 100
    assert sorted(background_sample(rows[:7])) == rows[:7]


def test_explanations_of_a_monotone_model_point_the_same_way_as_the_model():
    rng = np.random.default_rng(0)
    X = pd.DataFrame({
        "absence_percent": rng.uniform(0, 100, 400),
        "missing_submissions_count": rng.uniform(0, 20, 400),
    })
    X["missing_submissions_count"] += X["absence_percent"] / 5
    y = (90 - 0.4 * X["absence_percent"] - X["missing_submissions_count"] + np.sin(X["missing_submissions_count"]) * 8).tolist()
    model = IndexTrainer().train(
        X, y, list(range(400)),
        monotone_constraints={"absence_percent": -1, "missing_submissions_count": -1},
    ).model

    sweep = X.iloc[[0] * 30].copy()
    sweep["missing_submissions_count"] = np.linspace(0, 40, 30)
    shap_values = make_explainer(model, X.sample(100, random_state=0)).shap_values(sweep)[:, 1]

    assert np.all(np.diff(shap_values) <= 1e-6)
    assert shap_values[0] > 0 > shap_values[-1]


def test_contributions_are_ranked_by_absolute_shap_value():
    row = pd.Series({"avg_grade": 55.0, "absence_percent": 40.0, "course_year": 2.0})

    result = top_contributions(row, [0.1, -2.5, 0.7])

    assert [c["feature_name"] for c in result] == ["absence_percent", "course_year", "avg_grade"]
    assert [c["rank"] for c in result] == [1, 2, 3]
    assert result[0] == {"feature_name": "absence_percent", "feature_value": 40.0, "shap_value": -2.5, "rank": 1}


def test_only_the_top_n_are_kept():
    row = pd.Series({f"f{i}": float(i) for i in range(10)})

    assert len(top_contributions(row, list(range(10)), top_n=3)) == 3
