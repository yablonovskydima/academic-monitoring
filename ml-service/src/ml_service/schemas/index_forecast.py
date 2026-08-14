from pydantic import BaseModel, ConfigDict


class IndexForecastCreate(BaseModel):
    semesters_ahead: int
    predicted_index_value: float
    model_version_id: int


class IndexForecastOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_index_id: int
    semesters_ahead: int
    predicted_index_value: float
    model_version_id: int