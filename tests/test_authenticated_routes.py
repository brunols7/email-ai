from fastapi.testclient import TestClient
from sqlmodel import Session
from unittest.mock import MagicMock

from app.main import app
from app.category_routes import get_session
from app.models.category import Category
from app.models.email import Email

def test_create_category_passes(authenticated_client: TestClient, mocker):

    mocker.patch("fastapi.BackgroundTasks.add_task")
    mocker.patch("app.category_routes.set_sync_status")
    

    mock_session = MagicMock(spec=Session)


    app.dependency_overrides[get_session] = lambda: mock_session

    category_data = {"name": "Test Invoices", "description": "Invoices for testing"}


    response = authenticated_client.post("/categories", data=category_data, follow_redirects=False)


    assert response.status_code == 303, "A rota deveria redirecionar após a criação"
    assert response.headers["location"] == "/processing"


    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    

    app.dependency_overrides.clear()


def test_batch_delete_emails_passes(authenticated_client: TestClient, mocker):

    mock_batch_delete = mocker.patch("app.category_routes.batch_delete_emails")
    mock_session = MagicMock(spec=Session)
    

    app.dependency_overrides[get_session] = lambda: mock_session
    
    action_data = {"action": "delete", "email_ids": ["email1"]}
    
    response = authenticated_client.post("/categories/cat1/batch-action", data=action_data, follow_redirects=False)

    assert response.status_code == 303, "A rota deveria redirecionar após a ação"
    assert response.headers["location"] == "/categories/cat1"

    mock_batch_delete.assert_called_once()
    
    app.dependency_overrides.clear()