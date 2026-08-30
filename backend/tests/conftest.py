import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.auth.scopes import ALL_SCOPES
from app.core.auth.user import AuthUser
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app


@pytest.fixture
def sqlite_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db(sqlite_engine) -> Generator[Session]:
    SessionLocal = sessionmaker(bind=sqlite_engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()


@pytest.fixture
def actor() -> AuthUser:
    return AuthUser(
        subject="sub-ada",
        email="ada@example.com",
        name="Ada Admin",
        scopes=ALL_SCOPES,
    )


@pytest.fixture
def client(sqlite_engine, actor) -> Generator[TestClient]:
    SessionLocal = sessionmaker(bind=sqlite_engine, autoflush=False, autocommit=False)

    def override_db():
        session = SessionLocal()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    application = create_app(init_db=False)
    application.dependency_overrides[get_db] = override_db

    from app.api import deps

    application.dependency_overrides[deps.get_current_user] = lambda: actor
    with TestClient(application) as test_client:
        yield test_client


def mariadb_url() -> str | None:
    return os.environ.get("TEST_DATABASE_URL")
