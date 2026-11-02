import numpy as np
import pandas as pd

from ml_service.ml.training.index_trainer import IndexTrainer
from ml_service.ml.training.risk_trainer import RiskTrainer


def _noisy_data(n=400, seed=0):
    rng = np.random.default_rng(seed)
    X = pd.DataFrame({"absence_percent": rng.uniform(0, 100, n), "other": rng.uniform(0, 1, n)})
    wiggle = np.sin(X["absence_percent"] / 6.0) * 30
    groups = list(range(n))
    return X, wiggle, groups


def _sweep(X, column):
    grid = X.iloc[[0] * 50].copy()
    grid[column] = np.linspace(0, 100, 50)
    return grid


def test_constrained_regressor_never_rises_with_absence():
    X, wiggle, groups = _noisy_data()
    y = (80 - 0.3 * X["absence_percent"] + wiggle).tolist()

    model = IndexTrainer().train(X, y, groups, monotone_constraints={"absence_percent": -1}).model

    predictions = model.predict(_sweep(X, "absence_percent"))
    assert np.all(np.diff(predictions) <= 1e-6)


def test_constrained_classifier_risk_never_falls_with_absence():
    X, wiggle, groups = _noisy_data()
    y = ((X["absence_percent"] + wiggle) > 50).astype(int).tolist()

    model = RiskTrainer().train(X, y, groups, monotone_constraints={"absence_percent": 1}).model

    probabilities = model.predict_proba(_sweep(X, "absence_percent"))[:, 1]
    assert np.all(np.diff(probabilities) >= -1e-6)
