from fastapi.responses import JSONResponse
from sqlalchemy.orm import sessionmaker
from src import version
from src.db.models import User

def test_create_user(client, postgres_engine):
    username = "manukko2"
    password = "r1S0tt0N&"
    email = "pipino@language.com"

    body = {"username":username,"password":password, "email": email}
    response: JSONResponse = client.post(f"/api/{version}/users/register", json=body)
    print(response.json())
    assert response.status_code == 200

    with sessionmaker(bind=postgres_engine)() as db:
        created_user = db.query(User).filter(User.username == username).first()

        assert created_user is not None
        assert created_user.username == username
        assert created_user.email == email