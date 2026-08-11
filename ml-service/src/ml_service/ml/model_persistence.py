from datetime import datetime
from pathlib import Path

import joblib
from xgboost import XGBRegressor

MODELS_DIR = Path(__file__).resolve().parents[3] / "trained_models"


class ModelPersistence:
    def __init__(self, models_dir: Path | None = None):
        self.models_dir = models_dir or MODELS_DIR
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def save(self, model: XGBRegressor, version_label: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"model_{version_label}_{timestamp}.pkl"
        filepath = self.models_dir / filename

        joblib.dump(model, filepath)

        return str(filepath)

    def load(self, model_file_path: str) -> XGBRegressor:
        return joblib.load(model_file_path)