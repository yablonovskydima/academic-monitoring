from dataclasses import dataclass
from datetime import date, datetime

from ml_service.models.model_version import ModelPurpose
from ml_service.services.model_promotion_service import ModelPromotionService


@dataclass
class FakeVersion:
    id: int
    version_label: str
    algorithm: str
    purpose: ModelPurpose
    trained_at: datetime
    training_data_from: date
    training_data_to: date
    metrics: dict
    model_file_path: str
    is_active: bool


class FakeModelVersionService:
    def __init__(self):
        self.versions: list[FakeVersion] = []
        self._next_id = 1

    def get_active_by_purpose(self, purpose):
        return next(
            (v for v in self.versions if v.purpose == purpose and v.is_active), None,
        )

    def get_all_by_purpose(self, purpose):
        return [v for v in self.versions if v.purpose == purpose]

    def create(self, data):
        if data.is_active:
            for v in self.versions:
                if v.purpose == data.purpose:
                    v.is_active = False

        version = FakeVersion(
            id=self._next_id,
            version_label=data.version_label,
            algorithm=data.algorithm,
            purpose=data.purpose,
            trained_at=data.trained_at,
            training_data_from=data.training_data_from,
            training_data_to=data.training_data_to,
            metrics=data.metrics,
            model_file_path=data.model_file_path,
            is_active=data.is_active,
        )
        self._next_id += 1
        self.versions.append(version)
        return version

    def delete(self, version_id):
        self.versions = [v for v in self.versions if v.id != version_id]
        return True


class FakeModelPersistence:
    def delete(self, model_file_path):
        pass

    def load(self, model_file_path):
        return f"model-at-{model_file_path}"


def register(service, purpose, metrics, version_label):
    return service.register(
        purpose=purpose,
        version_label=version_label,
        algorithm="XGBRegressor",
        trained_at=datetime.now(),
        training_data_from=date(2024, 1, 1),
        training_data_to=date(2024, 6, 1),
        metrics=metrics,
        model_file_path=f"/tmp/{version_label}.pkl",
    )


def test_first_version_is_always_promoted():
    service = ModelPromotionService(FakeModelVersionService(), FakeModelPersistence())

    result = register(service, ModelPurpose.index_regression, {"r2": 0.5}, "v1")

    assert result.promoted is True
    assert result.warning is None
    assert result.version.is_active is True


def test_a_better_version_gets_promoted_and_deactivates_the_old_one():
    version_service = FakeModelVersionService()
    service = ModelPromotionService(version_service, FakeModelPersistence())

    v1 = register(service, ModelPurpose.index_regression, {"r2": 0.5}, "v1")
    v2 = register(service, ModelPurpose.index_regression, {"r2": 0.6}, "v2")

    assert v2.promoted is True
    assert v2.version.is_active is True
    assert v1.version.is_active is False


def test_a_worse_or_equal_version_is_not_promoted():
    version_service = FakeModelVersionService()
    service = ModelPromotionService(version_service, FakeModelPersistence())

    v1 = register(service, ModelPurpose.expulsion_classifier, {"f1": 0.6}, "v1")
    v2 = register(service, ModelPurpose.expulsion_classifier, {"f1": 0.6}, "v2")
    v3 = register(service, ModelPurpose.expulsion_classifier, {"f1": 0.4}, "v3")

    assert v2.promoted is False
    assert v2.warning is not None
    assert v3.promoted is False

    active = version_service.get_active_by_purpose(ModelPurpose.expulsion_classifier)
    assert active.version_label == v1.version.version_label


def test_load_active_model_returns_none_when_nothing_is_active():
    service = ModelPromotionService(FakeModelVersionService(), FakeModelPersistence())

    assert service.load_active_model(ModelPurpose.debt_classifier) is None


def test_load_active_model_loads_the_currently_active_file():
    version_service = FakeModelVersionService()
    service = ModelPromotionService(version_service, FakeModelPersistence())

    register(service, ModelPurpose.debt_classifier, {"f1": 0.7}, "v1")

    loaded = service.load_active_model(ModelPurpose.debt_classifier)
    assert loaded == "model-at-/tmp/v1.pkl"
