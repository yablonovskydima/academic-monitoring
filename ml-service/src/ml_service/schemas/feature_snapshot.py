from pydantic import BaseModel, ConfigDict


class FeatureSnapshotCreate(BaseModel):
    raw_features: dict


class FeatureSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_index_id: int
    raw_features: dict