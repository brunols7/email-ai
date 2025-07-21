import pytest
from typing import Generator
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine

from app.main import app
from app.db import engine as real_engine
from app.auth import get_session 
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def get_session_override() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


app.dependency_overrides[get_session] = get_session_override


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session, None, None]:
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session) -> TestClient:
    return TestClient(app)


@pytest.fixture(name="mocker")
def mocker_fixture(mocker):
    return mocker


@pytest.fixture
def authenticated_client(client: TestClient, mocker) -> TestClient:
    mock_user_data = {"email": "test@example.com", "name": "Test User"}
    mock_token_data = {"access_token": "fake_token", "client_id": "fake_id", "client_secret": "fake_secret"}

    mocker.patch("fastapi.Request.session", new_callable=MagicMock, return_value={
        "user": mock_user_data,
        "token": mock_token_data
    })

    return client