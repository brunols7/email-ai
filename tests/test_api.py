from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_home_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "AI Email Sorter" in response.text

def test_read_privacy_policy():
    response = client.get("/privacy")
    assert response.status_code == 200
    assert "Privacy Policy" in response.text

def test_dashboard_redirects_if_not_logged_in():

    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/"

def test_create_category_redirects_if_not_logged_in():

    response = client.post("/categories", data={"name": "Test", "description": "Test desc"}, follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/"