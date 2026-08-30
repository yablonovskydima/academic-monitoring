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
    WARM_START_N_ESTIMATORS = 50
    MAX_DEPTH = 4
    LEARNING_RATE = 0.1
    TEST_SIZE = 0.2
    RANDOM_STATE = 42
    MIN_TRAINING_SAMPLES = 50

    def train(
        self,
        X: pd.DataFrame,
        y: list[int],
        warm_start_model: XGBClassifier | None = None,
    ) -> RiskResult:
        if len(X) < self.MIN_TRAINING_SAMPLES:
            raise ValueError(
                f"Not enough training samples: got {len(X)}, need at least {self.MIN_TRAINING_SAMPLES}"
            )

        if len(set(y)) < 2:
            raise ValueError("Target has only one class — cannot train a classifier. Check your data.")

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.TEST_SIZE, random_state=self.RANDOM_STATE, stratify=y
        )

        positive_count = sum(y_train)
        negative_count = len(y_train) - positive_count
        scale_pos_weight = negative_count / positive_count if positive_count > 0 else 1.0

        warm_started = warm_start_model is not None
        model = self._make_model(warm_started, scale_pos_weight)

        try:
            if warm_started:
                model.fit(X_train, y_train, xgb_model=warm_start_model.get_booster())
            else:
                model.fit(X_train, y_train)
        except Exception as e:
            print(f"[risk_trainer] warm-start failed ({e}), falling back to cold start")
            warm_started = False
            model = self._make_model(warm_started, scale_pos_weight)
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
            "warm_started": warm_started,
        }

        return RiskResult(model=model, metrics=metrics)

    def _make_model(self, warm_started: bool, scale_pos_weight: float) -> XGBClassifier:
        return XGBClassifier(
            n_estimators=self.WARM_START_N_ESTIMATORS if warm_started else self.N_ESTIMATORS,
            max_depth=self.MAX_DEPTH,
            learning_rate=self.LEARNING_RATE,
            random_state=self.RANDOM_STATE,
            eval_metric="logloss",
            scale_pos_weight=scale_pos_weight,
        )
