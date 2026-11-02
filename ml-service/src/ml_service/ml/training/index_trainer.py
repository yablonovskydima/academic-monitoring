import pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_absolute_error, r2_score
from xgboost import XGBRegressor


class TrainingResult:
    def __init__(self, model: XGBRegressor, metrics: dict):
        self.model = model
        self.metrics = metrics


class IndexTrainer:
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
        y: list[float],
        groups: list[int],
        monotone_constraints: dict[str, int] | None = None,
        warm_start_model: XGBRegressor | None = None,
    ) -> TrainingResult:
        if len(X) < self.MIN_TRAINING_SAMPLES:
            raise ValueError(
                f"Not enough training samples: got {len(X)}, need at least {self.MIN_TRAINING_SAMPLES}"
            )

        splitter = GroupShuffleSplit(n_splits=1, test_size=self.TEST_SIZE, random_state=self.RANDOM_STATE)
        train_idx, test_idx = next(splitter.split(X, y, groups))
        y_series = pd.Series(y)
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y_series.iloc[train_idx].tolist(), y_series.iloc[test_idx].tolist()

        warm_started = warm_start_model is not None
        model = self._make_model(warm_started, monotone_constraints)

        try:
            if warm_started:
                model.fit(X_train, y_train, xgb_model=warm_start_model.get_booster())
            else:
                model.fit(X_train, y_train)
        except Exception as e:
            print(f"[index_trainer] warm-start failed ({e}), falling back to cold start")
            warm_started = False
            model = self._make_model(warm_started, monotone_constraints)
            model.fit(X_train, y_train)

        predictions = model.predict(X_test)

        metrics = {
            "mae": float(mean_absolute_error(y_test, predictions)),
            "r2": float(r2_score(y_test, predictions)),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "warm_started": warm_started,
        }

        return TrainingResult(model=model, metrics=metrics)

    def _make_model(self, warm_started: bool, monotone_constraints: dict[str, int] | None) -> XGBRegressor:
        return XGBRegressor(
            monotone_constraints=monotone_constraints,
            n_estimators=self.WARM_START_N_ESTIMATORS if warm_started else self.N_ESTIMATORS,
            max_depth=self.MAX_DEPTH,
            learning_rate=self.LEARNING_RATE,
            random_state=self.RANDOM_STATE,
        )
