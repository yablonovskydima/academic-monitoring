from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Date, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ml_service.database import Base

if TYPE_CHECKING:
    from ml_service.models.student_index import StudentIndex


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    version_label: Mapped[str] = mapped_column(String(50))
    algorithm: Mapped[str] = mapped_column(String(100))
    trained_at: Mapped[datetime]
    training_data_from: Mapped[date]
    training_data_to: Mapped[date]
    metrics: Mapped[dict] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    model_file_path: Mapped[str] = mapped_column(String(500))

    student_indexes: Mapped[list["StudentIndex"]] = relationship(back_populates="model_version")