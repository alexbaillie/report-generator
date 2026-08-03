"""
API tests using pytest.

These tests run against an isolated in-memory SQLite database via a dependency
override, so running the suite NEVER touches the production data/reports.db.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from main import app
from database.db import Base, get_db

# Dedicated in-memory engine for tests. StaticPool keeps a single shared
# connection so the schema created in the fixture is visible to every request.
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Route every endpoint's DB dependency to the isolated test database.
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables in the in-memory test DB before each test and drop after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


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
