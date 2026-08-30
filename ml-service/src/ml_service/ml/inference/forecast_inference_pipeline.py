from ml_service.ml.encoding.feature_encoder import FeatureEncoder
from ml_service.ml.persistence.model_persistence import ModelPersistence
from ml_service.services.model_version_service import ModelVersionService
from ml_service.services.index_forecast_service import IndexForecastService
from ml_service.schemas.index_forecast import IndexForecastCreate
from ml_service.models.model_version import ModelPurpose

FORECAST_HORIZONS = {
    ModelPurpose.index_forecast_horizon_2: 2,
    ModelPurpose.index_forecast_horizon_3: 3,
}


class ForecastInferencePipeline:
    def __init__(
        self,
        feature_encoder: FeatureEncoder,
        model_persistence: ModelPersistence,
        model_version_service: ModelVersionService,
        forecast_service: IndexForecastService,
    ):
        self.feature_encoder = feature_encoder
        self.model_persistence = model_persistence
        self.model_version_service = model_version_service
        self.forecast_service = forecast_service

        self._versions: dict = {}
        self._models: dict = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        for purpose in FORECAST_HORIZONS:
            version = self.model_version_service.get_active_by_purpose(purpose)
            if version is None:
                print(f"Warning: no active {purpose.value} model — this horizon will be skipped")
                continue
            self._versions[purpose] = version
            self._models[purpose] = self.model_persistence.load(version.model_file_path)

        self._loaded = True

    def process_batch(self, batch, student_indexes) -> None:
        self._ensure_loaded()

        if not self._models:
            return

        X_encoded = self.feature_encoder.encode(batch)

        predictions = {
            purpose: model.predict(X_encoded[self.feature_encoder.columns_for(purpose)])
            for purpose, model in self._models.items()
        }

        all_forecasts: list[tuple[int, IndexForecastCreate]] = []

        for idx, student_index in enumerate(student_indexes):
            for purpose, pred_array in predictions.items():
                all_forecasts.append((
                    student_index.id,
                    IndexForecastCreate(
                        semesters_ahead=FORECAST_HORIZONS[purpose],
                        predicted_index_value=float(pred_array[idx]),
                        model_version_id=self._versions[purpose].id,
                    ),
                ))

        self.forecast_service.bulk_create_many(all_forecasts)