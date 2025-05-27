from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker, aliased
from src import version
from src.db.models import Word, WordTranslation, import_csvs_to_db
from src.db.models import USER_LANGUAGE
from fastapi import status
from src.tests.utils import create_user_get_access_token

GAMES_BASE_ROUTE = f"/api/{version}/games"
WRONG_ANSWER = "XXXXXXXXXXXXXXXYYYYYYY" # an answer which is always wrong

@pytest.mark.helper
def get_answers_from_foreign_language(engine: Engine, questions: list[str], language: str, n_valid_answers, n_correct_answers):
    answers = {}

    with sessionmaker(bind=engine)() as db:
        for word_index in range(n_correct_answers):
            word = questions[word_index]
            WordOriginalWord = aliased(Word)
            WordTranslationWord = aliased(Word)
            solution = (
                db.query(WordTranslation)
                .join(WordOriginalWord, WordOriginalWord.id == WordTranslation.word_id)
                .where(WordOriginalWord.language == language)
                .where(WordOriginalWord.text == word)
                .join(WordTranslationWord, WordTranslationWord.id == WordTranslation.translation_id)
            ).first()
            answers[word] = solution.translation.text
    for word_index in range(n_correct_answers, n_valid_answers):
        word = questions[word_index]
        answers[word] = WRONG_ANSWER

    questions[:] = [x for x in questions if x not in answers]
    return answers

@pytest.mark.helper
def get_answers_from_your_language(engine: Engine, questions: list[str], language: str, n_valid_answers, n_correct_answers):
    answers = {}

    with sessionmaker(bind=engine)() as db:
        for word_index in range(n_correct_answers):
            word = questions[word_index]
            WordOriginalWord = aliased(Word)
            WordTranslationWord = aliased(Word)
            solution = (
                db.query(WordTranslation)
                .join(WordTranslationWord, WordTranslationWord.id == WordTranslation.translation_id)
                .where(WordTranslationWord.language == language)
                .where(WordTranslationWord.text == word)
                .join(WordOriginalWord, WordOriginalWord.id == WordTranslation.word_id)
            ).first()
            answers[word] = solution.word.text
    for word_index in range(n_correct_answers, n_valid_answers):
        word = questions[word_index]
        answers[word] = WRONG_ANSWER

    questions[:] = [x for x in questions if x not in answers]
    return answers

def test_play_game_1(client: TestClient, postgres_engine):
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
    n_vocabulary = 300
    n_words_to_guess = 15
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


    words_from_foreign_language: list = response.json().get("from_foreign_language")
    n_game_correct_answers = 0
    n_game_answers = 0
    
    # give 3 wrong answers
    n_round_correct_answers = 0
    n_round_valid_answers = 3
    answers_from_foreign_language = get_answers_from_foreign_language(postgres_engine, words_from_foreign_language, language, n_round_valid_answers, n_round_correct_answers)

    body = {
        "from_foreign_language": answers_from_foreign_language
    }

    response: JSONResponse = client.post(f"{GAMES_BASE_ROUTE}/{id}/answers", json=body, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    n_game_correct_answers += n_round_correct_answers
    n_game_answers += n_round_valid_answers


    response_dict: dict = response.json().get("game")
    round_score_percentage: int = response.json().get("round_score_percentage")
    assert response_dict.get("n_remaining_words_to_guess") == len(words_from_foreign_language)
    assert response_dict.get("n_correct_answers") == n_game_correct_answers
    assert response_dict.get("game_score_percentage") == round(100*n_round_correct_answers/n_round_valid_answers, 2)
    assert round_score_percentage == round(100*n_game_correct_answers/n_game_answers, 2)

    # give 3 right answers
    n_round_correct_answers = 3
    n_round_valid_answers = 3
    answers_from_foreign_language = get_answers_from_foreign_language(postgres_engine, words_from_foreign_language, language, n_round_valid_answers, n_round_correct_answers)

    body = {
        "from_foreign_language": answers_from_foreign_language
    }

    response: JSONResponse = client.post(f"{GAMES_BASE_ROUTE}/{id}/answers", json=body, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    n_game_correct_answers += n_round_correct_answers
    n_game_answers += n_round_valid_answers

    response_dict: dict = response.json().get("game")
    round_score_percentage: int = response.json().get("round_score_percentage")
    assert response_dict.get("n_remaining_words_to_guess") == len(words_from_foreign_language)
    assert response_dict.get("n_correct_answers") == n_game_correct_answers
    assert response_dict.get("game_score_percentage") == round(100*n_game_correct_answers/n_game_answers, 2)
    assert round_score_percentage == round(100*n_round_correct_answers/n_round_valid_answers, 2)
    
    # give 3 right, 2 wrong answers and 2 invalid answers
    n_round_valid_answers = 5
    n_round_correct_answers = 3
    answers_from_foreign_language = get_answers_from_foreign_language(postgres_engine, words_from_foreign_language, language, n_round_valid_answers, n_round_correct_answers)

    # generate two more invalid answers (must be ignored from the logic)
    for _ in range(0, 2):
        answers_from_foreign_language[WRONG_ANSWER] = WRONG_ANSWER

    body = {
        "from_foreign_language": answers_from_foreign_language
    }

    response: JSONResponse = client.post(f"{GAMES_BASE_ROUTE}/{id}/answers", json=body, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    n_game_answers += n_round_valid_answers
    n_game_correct_answers += n_round_correct_answers

    response_dict: dict = response.json().get("game")
    round_score_percentage: int = response.json().get("round_score_percentage")
    assert response_dict.get("n_remaining_words_to_guess") == len(words_from_foreign_language)
    assert response_dict.get("n_correct_answers") == n_game_correct_answers
    assert response_dict.get("game_score_percentage") == round(100*n_game_correct_answers/n_game_answers, 2)
    assert round_score_percentage == round(100*n_round_correct_answers/n_round_valid_answers, 2)


def test_play_game_2(client: TestClient, postgres_engine):
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
    n_vocabulary = 250
    n_words_to_guess = 30
    game_type = "random"
    translate_from_your_language_percentage = 50

    body = {
        "language": language,
        "n_vocabulary": n_vocabulary,
        "n_words_to_guess": n_words_to_guess,
        "type": game_type,
        "translate_from_your_language_percentage": translate_from_your_language_percentage
    }

    response: JSONResponse = client.post(f"{GAMES_BASE_ROUTE}/new", json=body, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    id = response.json().get("id")


    words_from_foreign_language: list = response.json().get("from_foreign_language")
    words_from_your_language: list = response.json().get("from_your_language")
    n_game_correct_answers = 0
    n_game_answers = 0

    # give 3 right answers in your language
    n_round_correct_answers = 3
    n_round_valid_answers = 3
    answers_from_foreign_language = get_answers_from_foreign_language(postgres_engine, words_from_foreign_language, language, n_round_valid_answers, n_round_correct_answers)

    body = {
        "from_foreign_language": answers_from_foreign_language
    }

    response: JSONResponse = client.post(f"{GAMES_BASE_ROUTE}/{id}/answers", json=body, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    n_game_correct_answers += n_round_correct_answers
    n_game_answers += n_round_valid_answers

    response_dict: dict = response.json().get("game")
    round_score_percentage: int = response.json().get("round_score_percentage")
    assert response_dict.get("n_remaining_words_to_guess") == len(words_from_foreign_language) + len(words_from_your_language)
    assert response_dict.get("n_correct_answers") == n_game_correct_answers
    assert response_dict.get("game_score_percentage") == round(100*n_game_correct_answers/n_game_answers, 2)
    assert round_score_percentage == round(100*n_round_correct_answers/n_round_valid_answers, 2)
    
    # give 3 right, 2 wrong answers in foreign language
    n_round_valid_answers_foreign = 5
    n_round_correct_answers_foreing = 3
    n_round_valid_answers_yours = 5
    n_round_correct_answers_yours = 2
    n_round_valid_answers = n_round_valid_answers_foreign + n_round_valid_answers_yours
    n_round_correct_answers = n_round_correct_answers_foreing + n_round_correct_answers_yours
    answers_from_foreign_language = get_answers_from_foreign_language(postgres_engine, words_from_foreign_language, language, n_round_valid_answers_foreign, n_round_correct_answers_foreing)
    answers_from_your_language = get_answers_from_your_language(postgres_engine, words_from_your_language, USER_LANGUAGE, n_round_valid_answers_yours, n_round_correct_answers_yours)
    
    body = {
        "from_foreign_language": answers_from_foreign_language,
        "from_your_language": answers_from_your_language
    }

    response: JSONResponse = client.post(f"{GAMES_BASE_ROUTE}/{id}/answers", json=body, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    n_game_answers += n_round_valid_answers
    n_game_correct_answers += n_round_correct_answers

    response_dict: dict = response.json().get("game")
    round_score_percentage: int = response.json().get("round_score_percentage")
    assert response_dict.get("n_remaining_words_to_guess") == len(words_from_foreign_language) + len(words_from_your_language)
    assert response_dict.get("n_correct_answers") == n_game_correct_answers
    assert response_dict.get("game_score_percentage") == round(100*n_game_correct_answers/n_game_answers, 2)
    assert round_score_percentage == round(100*n_round_correct_answers/n_round_valid_answers, 2)
