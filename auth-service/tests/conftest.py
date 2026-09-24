import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from auth_service.database import Base, get_db
from auth_service.main import app
from auth_service.models import (  # noqa: F401
    audit_log,
    curator_group_assignment,
    dean_faculty_assignment,
    password_reset_token,
    refresh_token,
    user,
)
from auth_service.rate_limit import reset_rate_limiter


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    reset_rate_limiter()
    yield


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()
