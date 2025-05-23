from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from src import version
from src.db.models import import_csvs_to_db
from unittest.mock import patch
from fastapi import status
from src.tests.utils import create_user_get_access_token

GAMES_BASE_ROUTE = f"/api/{version}/games"

def test_create_game(client: TestClient, postgres_engine):
    username = "manukko_poli"
    password = "4nCh3S3nZ4B3r&"
    email = "manukko_poli@studenti.polimi.it"

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
    id = response.json().get("id")
    # TODO: continue test
