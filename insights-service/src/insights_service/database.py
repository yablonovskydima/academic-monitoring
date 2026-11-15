import os
from typing import Generator

from dotenv import load_dotenv, find_dotenv
from sqlalchemy import BigInteger, Integer, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv(find_dotenv())

DB_USER = os.getenv("DB_USER_INSIGHTS_SERVICE")
DB_PASSWORD = os.getenv("DB_PASSWORD_INSIGHTS_SERVICE")
DB_HOST = os.getenv("DB_HOST_INSIGHTS_SERVICE")
DB_PORT = os.getenv("DB_PORT_INSIGHTS_SERVICE")
DB_NAME = os.getenv("DB_NAME_INSIGHTS_SERVICE")

if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
    raise RuntimeError("Database env error.")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


BigIntegerPK = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from insights_service.models import (  # noqa: F401
        insight_run, student_insight, risk_insight, insight_reason, insight_forecast, insight_change, group_summary,
    )
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
