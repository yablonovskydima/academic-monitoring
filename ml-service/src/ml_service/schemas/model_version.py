from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from ml_service.models.model_version import ModelPurpose


class ModelVersionCreate(BaseModel):
    version_label: str
    algorithm: str
    purpose: ModelPurpose
    trained_at: datetime
    training_data_from: date
    training_data_to: date
    metrics: dict
    model_file_path: str
    is_active: bool = False


class ModelVersionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: bool | None = None
    metrics: dict | None = None


class ModelVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version_label: str
    algorithm: str
    purpose: ModelPurpose
    trained_at: datetime
    training_data_from: date
    training_data_to: date
    metrics: dict
    is_active: bool
    model_file_path: str