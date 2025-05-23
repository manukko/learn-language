from fastapi.responses import JSONResponse
from sqlalchemy.orm import sessionmaker
from src import version
from src.db.models import User

def test_create_user_twice(client, postgres_engine):
    username = "prodigioso"
    password = "r1S0tt0N&"
    email = "prodigioso@pipino.com"

    body = {"username":username,"password":password, "email": email}
    response: JSONResponse = client.post(f"/api/{version}/users/register", json=body)
    assert response.status_code == 200

    with sessionmaker(bind=postgres_engine)() as db:
        created_user = db.query(User).filter(User.username == username).first()

        assert created_user is not None
        assert created_user.username == username
        assert created_user.email == email

    body = {"username":username,"password":password, "email": email}
    response: JSONResponse = client.post(f"/api/{version}/users/register", json=body)
    assert response.status_code == 409

def test_create_user_password_invalid(client):
    username = "pirlottero"
    password = "easy"
    email = "pirlottero@pirlero.com"

    body = {"username":username,"password":password, "email": email}
    response: JSONResponse = client.post(f"/api/{version}/users/register", json=body)
    assert response.status_code == 403