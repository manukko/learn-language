from fastapi.testclient import TestClient
from src import app

client = TestClient(app)

def test_default():
    response = client.get("/")
    print(response.text)
    assert response.status_code == 200