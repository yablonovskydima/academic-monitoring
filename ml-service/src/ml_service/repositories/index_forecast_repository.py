from sqlalchemy import select
from sqlalchemy.orm import Session

from ml_service.models.index_forecast import IndexForecast


class IndexForecastRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, forecast_id: int) -> IndexForecast | None:
        return self.session.scalars(
            select(IndexForecast).where(IndexForecast.id == forecast_id)
        ).first()

    def get_by_student_index(self, student_index_id: int) -> list[IndexForecast]:
        return list(self.session.scalars(
            select(IndexForecast)
            .where(IndexForecast.student_index_id == student_index_id)
            .order_by(IndexForecast.semesters_ahead)
        ).all())

    def save(self, forecast: IndexForecast) -> IndexForecast:
        self.session.add(forecast)
        self.session.flush()
        self.session.commit()
        return forecast

    def bulk_save(self, forecasts: list[IndexForecast]) -> list[IndexForecast]:
        self.session.add_all(forecasts)
        self.session.flush()
        self.session.commit()
        return forecasts

    def delete(self, forecast_id: int) -> bool:
        forecast = self.get_by_id(forecast_id)
        if forecast is None:
            return False
        self.session.delete(forecast)
        self.session.commit()
        return True