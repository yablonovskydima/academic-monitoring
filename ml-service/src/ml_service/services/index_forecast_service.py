from sqlalchemy.orm import Session

from ml_service.models.index_forecast import IndexForecast
from ml_service.repositories.index_forecast_repository import IndexForecastRepository
from ml_service.schemas.index_forecast import IndexForecastCreate


class IndexForecastService:
    def __init__(self, db: Session):
        self.repo = IndexForecastRepository(db)

    def get_by_student_index(self, student_index_id: int) -> list[IndexForecast]:
        return self.repo.get_by_student_index(student_index_id)

    def create(self, student_index_id: int, data: IndexForecastCreate) -> IndexForecast:
        forecast = IndexForecast(student_index_id=student_index_id, **data.model_dump())
        return self.repo.save(forecast)

    def bulk_create(
        self, student_index_id: int, items_data: list[IndexForecastCreate]
    ) -> list[IndexForecast]:
        forecasts = [
            IndexForecast(student_index_id=student_index_id, **data.model_dump())
            for data in items_data
        ]
        return self.repo.bulk_save(forecasts)

    def delete(self, forecast_id: int) -> bool:
        return self.repo.delete(forecast_id)