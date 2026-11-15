import os

for _name, _value in {
    "DB_USER_INSIGHTS_SERVICE": "test",
    "DB_PASSWORD_INSIGHTS_SERVICE": "test",
    "DB_HOST_INSIGHTS_SERVICE": "localhost",
    "DB_PORT_INSIGHTS_SERVICE": "5435",
    "DB_NAME_INSIGHTS_SERVICE": "test",
}.items():
    os.environ.setdefault(_name, _value)

import pytest  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from insights_service.database import Base  # noqa: E402
from insights_service.models import (  # noqa: E402, F401
    group_summary, insight_change, insight_forecast, insight_reason, insight_run, risk_insight, student_insight,
)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        yield session
    finally:
        session.close()
