from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_home_page():
    """Tests if the home page loads correctly for a visitor."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to Email AI" in response.text

def test_read_privacy_policy():
    """Tests if the privacy policy page loads correctly."""
    response = client.get("/privacy")
    assert response.status_code == 200
    assert "Privacy Policy" in response.text

def test_dashboard_redirects_if_not_logged_in():
    """Tests if the dashboard correctly redirects if the user is not logged in."""
    response = client.get("/dashboard", allow_redirects=False)
    assert response.status_code == 307

def test_create_category_redirects_if_not_logged_in():
    """Tests if creating a category redirects if the user is not logged in."""
    response = client.post("/categories", data={"name": "Test", "description": "Test desc"}, allow_redirects=False)
    assert response.status_code == 307