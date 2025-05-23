from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src import app
import pytest
from src.db.models import Base
from src.services.auth import get_db_session

@pytest.fixture(scope="function")
def postgres_engine():
    with PostgresContainer("postgres:15") as postgres:
        engine = create_engine(postgres.get_connection_url())
        Base.metadata.create_all(engine)
        yield engine

@pytest.fixture(scope="function")
def override_get_db(postgres_engine):
    TestingSessionLocal = sessionmaker(bind=postgres_engine)

    def _override():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db_session] = _override
    yield
    Base.metadata.drop_all(postgres_engine)
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def client(override_get_db):
    return TestClient(app)