from typing import Tuple
from unittest.mock import MagicMock, patch
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from fastapi import status
from sqlalchemy import Engine
from src import version
import pytest

from src.db.models import User


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
def get_refresh_token_for_user(client: TestClient, username: str | None, password: str | None):
    data={
        "username": username,
        "password": password
    }
    headers={"Content-Type": "application/x-www-form-urlencoded"}
    response: JSONResponse = client.post(f"/api/{version}/users/get_refresh_token", data=data, headers=headers)
    return response

@pytest.mark.helper
def create_user_get_access_token(client: TestClient, postgres_engine: Engine, username: str, password: str, email: str) -> Tuple[User, str]:

    response, _ = create_user(client, username, password, email)
    assert response.status_code == status.HTTP_201_CREATED
    
    response = get_access_token_for_user(client, username, password)
    assert response.status_code == status.HTTP_200_OK
    token = response.json().get("access_token")

    with sessionmaker(bind=postgres_engine)() as db:
        user = db.query(User).filter(User.username == username).first()
    assert user is not None
    assert user.username == username
    return user, token