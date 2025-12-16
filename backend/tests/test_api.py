"""
API tests using pytest
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from database.db import Base, engine

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test and drop after"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_template():
    """Test creating a template"""
    template_data = {
        "name": "Test Template",
        "description": "A test template",
        "template_type": "intake",
        "content": "Test content",
        "is_default": False
    }
    response = client.post("/api/templates/", json=template_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == template_data["name"]
    assert "id" in data

def test_list_templates():
    """Test listing templates"""
    response = client.get("/api/templates/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_list_reports():
    """Test listing reports"""
    response = client.get("/api/reports/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_list_documents():
    """Test listing documents"""
    response = client.get("/api/documents/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
