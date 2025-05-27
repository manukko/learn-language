from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from src import version
from src.db.models import import_csvs_to_db
from fastapi import status
from src.tests.utils import create_user_get_access_token

GAMES_BASE_ROUTE = f"/api/{version}/games"

def test_create_game(client: TestClient, postgres_engine):
    username = "mariosette"
    password = "Pr1m0L3v1"
    email = "mariosette@libero.org"

    with sessionmaker(bind=postgres_engine)() as db:
        import_csvs_to_db(db)
    _, access_token = create_user_get_access_token(client, postgres_engine, username, password, email)

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    language = "german"
    n_vocabulary = 100
    n_words_to_guess = 5
    game_type = "random"

    body = {
        "language": language,
        "n_vocabulary": n_vocabulary,
        "n_words_to_guess": n_words_to_guess,
        "type": game_type
    }

    response: JSONResponse = client.post(f"{GAMES_BASE_ROUTE}/new", json=body, headers=headers)

    assert response.status_code == status.HTTP_201_CREATED
    game1_id = response.json().get("id")
    assert response.json().get("language") == language
    assert response.json().get("n_vocabulary") == n_vocabulary

    response: JSONResponse = client.get(f"{GAMES_BASE_ROUTE}/", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("games")[0].get("id") == game1_id
    response: JSONResponse = client.get(f"{GAMES_BASE_ROUTE}/active", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("games")[0].get("id") == game1_id


    response: JSONResponse = client.post(f"{GAMES_BASE_ROUTE}/new", json=body, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    game2_id = response.json().get("id")

    response: JSONResponse = client.get(f"{GAMES_BASE_ROUTE}/", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().get("games")) == 2
    response: JSONResponse = client.get(f"{GAMES_BASE_ROUTE}/active", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json().get("games")) == 2

    response: JSONResponse = client.get(f"{GAMES_BASE_ROUTE}/{game1_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == game1_id

    response: JSONResponse = client.get(f"{GAMES_BASE_ROUTE}/{game2_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == game2_id


def test_delete_game(client: TestClient, postgres_engine):
    username = "mariosette"
    password = "Pr1m0L3v1"
    email = "mariosette@libero.org"

    with sessionmaker(bind=postgres_engine)() as db:
        import_csvs_to_db(db)
    _, access_token = create_user_get_access_token(client, postgres_engine, username, password, email)

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    language = "german"
    n_vocabulary = 100
    n_words_to_guess_game1 = 5
    game_type = "random"

    body = {
        "language": language,
        "n_vocabulary": n_vocabulary,
        "n_words_to_guess": n_words_to_guess_game1,
        "type": game_type
    }

    response: JSONResponse = client.post(f"{GAMES_BASE_ROUTE}/new", json=body, headers=headers)
    id_game1 = response.json().get("id")
    assert response.status_code == status.HTTP_201_CREATED

    n_words_to_guess_game2 = 20
    body["n_words_to_guess"] = n_words_to_guess_game2
    response: JSONResponse = client.post(f"{GAMES_BASE_ROUTE}/new", json=body, headers=headers)
    id_game2 = response.json().get("id")
    assert response.status_code == status.HTTP_201_CREATED

    response: JSONResponse = client.delete(f"{GAMES_BASE_ROUTE}/{id_game1}", headers=headers)

    response: JSONResponse = client.get(f"{GAMES_BASE_ROUTE}/{id_game1}", headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    response: JSONResponse = client.get(f"{GAMES_BASE_ROUTE}/{id_game2}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json().get("id") == id_game2
