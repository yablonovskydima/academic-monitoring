import os

from dotenv import load_dotenv, find_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from typing import Generator
from sqlalchemy.orm import Session

load_dotenv(find_dotenv())

DB_USER = os.getenv("DB_USER_ML_SERVICE")
DB_PASSWORD = os.getenv("DB_PASSWORD_ML_SERVICE")
DB_HOST = os.getenv("DB_HOST_ML_SERVICE")
DB_PORT = os.getenv("DB_PORT_ML_SERVICE")
DB_NAME = os.getenv("DB_NAME_ML_SERVICE")

if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
    raise RuntimeError("Database env error.")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, echo=False, executemany_mode="values_plus_batch", insertmanyvalues_page_size=5000)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from ml_service.models import (
        model_version, student_index, index_explanation,
        feature_snapshot, risk_assessment, index_forecast,
    )
    Base.metadata.create_all(bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()