# app/test_tasks.py
from fastapi.testclient import TestClient
from app.main import app
from app.database import db  

db.create_tables()  

client = TestClient(app)

def test_create_task():
    response = client.post("/tasks/", json={"title": "Teste", "description": "Teste desc", "status": "pendente"})
    assert response.status_code == 200
    assert response.json()["title"] == "Teste"

def test_list_tasks():
    response = client.get("/tasks/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_update_task():
    task = client.post("/tasks/", json={"title": "Old", "description": "Desc", "status": "pendente"}).json()
    response = client.put(f"/tasks/{task['id']}", json={"title": "Updated"})
    assert response.status_code == 200
    assert response.json()["title"] == "Updated"

def test_delete_task():
    task = client.post("/tasks/", json={"title": "To Delete", "description": "Desc", "status": "pendente"}).json()
    response = client.delete(f"/tasks/25")
    assert response.status_code == 200