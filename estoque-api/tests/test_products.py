from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_create_product():
    response = client.post(
        "/products/",
        json={"name": "Test Product", "description": "Test Description", "price": 10.0, "quantity": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Product"
    assert "id" in data

def test_read_product():
    # First create a product
    response = client.post(
        "/products/",
        json={"name": "Test Product", "description": "Test Description", "price": 10.0, "quantity": 5},
    )
    product_id = response.json()["id"]

    # Then read it
    response = client.get(f"/products/{product_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Product"
    assert data["id"] == product_id

def test_read_products():
    response = client.get("/products/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_update_product():
    # First create a product
    response = client.post(
        "/products/",
        json={"name": "Test Product", "description": "Test Description", "price": 10.0, "quantity": 5},
    )
    product_id = response.json()["id"]

    # Then update it
    response = client.put(
        f"/products/{product_id}",
        json={"name": "Updated Product", "description": "Updated Description", "price": 15.0, "quantity": 10},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Product"
    assert data["price"] == 15.0

def test_delete_product():
    # First create a product
    response = client.post(
        "/products/",
        json={"name": "Test Product", "description": "Test Description", "price": 10.0, "quantity": 5},
    )
    product_id = response.json()["id"]

    # Then delete it
    response = client.delete(f"/products/{product_id}")
    assert response.status_code == 200

    # Verify it's deleted
    response = client.get(f"/products/{product_id}")
    assert response.status_code == 404
