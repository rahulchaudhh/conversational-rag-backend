from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_serves_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "Conversational RAG" in response.text
    assert "text/html" in response.headers.get("content-type", "")

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_get_documents():
    response = client.get("/documents/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_bookings():
    response = client.get("/chat/bookings")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
