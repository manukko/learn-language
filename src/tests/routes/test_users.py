from typing import Tuple
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import sessionmaker
from src import version
from src.db.models import User
from unittest.mock import MagicMock, patch
from fastapi import status
from src.services.auth import create_url_safe_token, verify_password

@pytest.mark.helper
def create_user(client: TestClient, username: str | None, password: str | None, email: str | None) -> Tuple[JSONResponse, MagicMock]:
    with patch("src.routes.users.BackgroundTasks.add_task") as mock_send_email_task:
        body = {}
        if username is not None:
            body["username"] = username
        if password is not None:
            body["password"] = password
        if email is not None:
            body["email"] = email
        response: JSONResponse = client.post(f"/api/{version}/users/register", json=body)
        return response, mock_send_email_task

@pytest.mark.helper
def get_access_token_for_user(client: TestClient, username: str | None, password: str | None):
    data={
        "username": username,
        "password": password
    }
    headers={"Content-Type": "application/x-www-form-urlencoded"}
    response: JSONResponse = client.post(f"/api/{version}/users/get_access_token", data=data, headers=headers)
    return response

@pytest.mark.helper
def get_access_refresh_for_user(client: TestClient, username: str | None, password: str | None):
    data={
        "username": username,
        "password": password
    }
    headers={"Content-Type": "application/x-www-form-urlencoded"}
    response: JSONResponse = client.post(f"/api/{version}/users/get_refresh_token", data=data, headers=headers)
    return response

def test_create_user_twice(client: TestClient, postgres_engine):
    username = "prodigioso"
    password = "r1S0tt0N&"
    email = "prodigioso@pipino.com"

    response, mock_send_email_task = create_user(client, username, password, email)
    assert response.status_code == status.HTTP_201_CREATED
    mock_send_email_task.assert_called_once()

    with sessionmaker(bind=postgres_engine)() as db:
        user = db.query(User).filter(User.username == username).first()

        assert user is not None
        assert user.username == username
        assert user.email == email
        assert not user.is_verified

    response, mock_send_email_task = create_user(client, username, password, email)
    assert response.status_code == status.HTTP_409_CONFLICT

def test_create_verify_user(client: TestClient, postgres_engine):
    username = "mariosette"
    password = "Pr1m0L3v1"
    email = "mariosette@libero.org"

    response, mock_send_email_task = create_user(client, username, password, email)
    assert response.status_code == status.HTTP_201_CREATED
    mock_send_email_task.assert_called_once()

    token = create_url_safe_token({"email": email})
    response: JSONResponse = client.get(f"/api/{version}/users/verify/{token}")
    assert response.status_code == status.HTTP_200_OK

    with sessionmaker(bind=postgres_engine)() as db:
        user = db.query(User).filter(User.username == username).first()
        assert user is not None
        assert user.username == username
        assert user.email == email
        assert user.is_verified


def test_create_user_password_invalid(client: TestClient):
    username = "pirlottero"
    password = "easy"
    email = "pirlottero@pirlero.com"

    response, mock_send_email_task = create_user(client, username, password, email)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    mock_send_email_task.assert_not_called()

def test_create_user_body_invalid(client: TestClient):
    email = "gianni.infantile@aruba.com"
    response, mock_send_email_task = create_user(client, None, None, email)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    mock_send_email_task.assert_not_called()

    username = "gianni.infantile"
    password = "r1S0tt0N&77"
    response, mock_send_email_task = create_user(client, username, password, None)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    mock_send_email_task.assert_not_called()


def test_delete_user(client: TestClient, postgres_engine):
    username = "mariosette"
    password = "Pr1m0L3v1"
    email = "mariosette@libero.org"
    response, _ = create_user(client, username, password, email)

    assert response.status_code == status.HTTP_201_CREATED
    
    response = get_access_token_for_user(client, username, password)
    assert response.status_code == status.HTTP_200_OK

    token = response.json().get("access_token")

    with sessionmaker(bind=postgres_engine)() as db:
        user = db.query(User).filter(User.username == username).first()
        assert user is not None
        assert user.username == username
        assert user.email == email
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response: JSONResponse = client.delete(f"/api/{version}/users/delete", headers=headers)
    assert response.status_code == status.HTTP_200_OK


def test_refresh_token_logout(client: TestClient, postgres_engine):
    username = "mariosette"
    password = "Pr1m0L3v1"
    email = "mariosette@libero.org"
    response, _ = create_user(client, username, password, email)

    assert response.status_code == status.HTTP_201_CREATED
    
    response = get_access_refresh_for_user(client, username, password)
    assert response.status_code == status.HTTP_200_OK
    refresh_token = response.json().get("refresh_token")

    headers = {
        "Authorization": f"Bearer {refresh_token}"
    }
    response: JSONResponse = client.get(f"/api/{version}/users/refresh_access_token", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    access_token = response.json().get("access_token")

    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response: JSONResponse = client.get(f"/api/{version}/users/me", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("username") == username
    assert response.json().get("email") == email

    response: JSONResponse = client.get(f"/api/{version}/users/logout", headers=headers)
    assert response.status_code == status.HTTP_200_OK

    response: JSONResponse = client.get(f"/api/{version}/users/me", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED



def test_get_link_reset_password(client: TestClient, postgres_engine):
    username = "mariosette"
    password = "Pr1m0L3v1"
    email = "mariosette@libero.org"
    response, _ = create_user(client, username, password, email)
    assert response.status_code == status.HTTP_201_CREATED

    with patch("src.routes.users.BackgroundTasks.add_task") as mock_send_email_task:
        response: JSONResponse = client.post(f"/api/{version}/users/send_reset_password_link", json={"email": email})
        assert response.status_code == status.HTTP_200_OK
        mock_send_email_task.assert_called_once()

    with sessionmaker(bind=postgres_engine)() as db:
        user = db.query(User).filter(User.username == username).first()
        assert user is not None
        assert user.username == username
        assert user.email == email
        assert verify_password(password, user.hashed_password)

    reset_password_token = create_url_safe_token({"email": email})

    new_password = "S3c0nd0M1c0lM"
    body = {"password": new_password, "confirm_password": new_password}
    response: JSONResponse = client.post(f"/api/{version}/users/reset_password/{reset_password_token}", json=body)
    assert response.status_code == status.HTTP_200_OK

    with sessionmaker(bind=postgres_engine)() as db:
        user = db.query(User).filter(User.username == username).first()
        assert user is not None
        assert user.username == username
        assert user.email == email
        assert verify_password(new_password, user.hashed_password)