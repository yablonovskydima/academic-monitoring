import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from xgboost import XGBClassifier


class RiskResult:
    def __init__(self, model: XGBClassifier, metrics: dict):
        self.model = model
        self.metrics = metrics


class RiskTrainer:
    N_ESTIMATORS = 200
    MAX_DEPTH = 4
    LEARNING_RATE = 0.1
    TEST_SIZE = 0.2
    RANDOM_STATE = 42
    MIN_TRAINING_SAMPLES = 50

    def train(self, X: pd.DataFrame, y: list[int]) -> RiskResult:
        if len(X) < self.MIN_TRAINING_SAMPLES:
            raise ValueError(
                f"Not enough training samples: got {len(X)}, need at least {self.MIN_TRAINING_SAMPLES}"
            )

        if len(set(y)) < 2:
            raise ValueError("Target has only one class — cannot train a classifier. Check your data.")

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.TEST_SIZE, random_state=self.RANDOM_STATE, stratify=y
        )

        model = XGBClassifier(
            n_estimators=self.N_ESTIMATORS,
            max_depth=self.MAX_DEPTH,
            learning_rate=self.LEARNING_RATE,
            random_state=self.RANDOM_STATE,
            eval_metric="logloss",
        )
        model.fit(X_train, y_train)

        predictions = model.predict(X_test)

        metrics = {
            "accuracy": float(accuracy_score(y_test, predictions)),
            "precision": float(precision_score(y_test, predictions, zero_division=0)),
            "recall": float(recall_score(y_test, predictions, zero_division=0)),
            "f1": float(f1_score(y_test, predictions, zero_division=0)),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "positive_rate": float(sum(y) / len(y)),
        }

        return RiskResult(model=model, metrics=metrics)