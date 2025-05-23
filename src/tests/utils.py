from typing import Tuple
from unittest.mock import MagicMock, patch
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from src import version
import pytest


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