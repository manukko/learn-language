from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker
from src import app
import pytest
from src.db.models import Base
from src.services.auth import get_db_session

@pytest.fixture(scope="session")
def postgres_container():
    container = PostgresContainer("postgres:15")
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="session")
def postgres_engine(postgres_container: PostgresContainer):
    engine: Engine = create_engine(postgres_container.get_connection_url())
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def override_get_db(postgres_engine: Engine):
    TestingSessionLocal = sessionmaker(bind=postgres_engine)

    def _override():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db_session] = _override
    yield
    # Truncate all tables after each test (keeping schema)
    with postgres_engine.connect() as connection:
        trans = connection.begin()
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
        trans.commit()

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(override_get_db):
    return TestClient(app)