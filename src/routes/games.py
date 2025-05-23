from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from src.services.auth import (
    get_db_session,
    get_current_user_factory
)
from src.db.models import User
from src.schemas.games import GameCreateInputModel, GameDetailOutputModel
from src.schemas.games import AnswerInputModel
from src.services.games import GameService

router = APIRouter()
game_service = GameService()

@router.post("/new", status_code=status.HTTP_201_CREATED, response_model=GameDetailOutputModel)
def create_game(
    game_create_model: GameCreateInputModel,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_factory()),
    ):

    language = game_create_model.language.lower()

    new_game = game_service.create_new_game(
        db, 
        current_user, 
        language, 
        game_create_model.n_words_to_guess, 
        game_create_model.n_vocabulary,
        game_create_model.type,
        game_create_model.translate_from_your_language_percentage
    )

    return new_game
@router.get("/active")
def get_active_games_for_user(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_factory()),
    ):
    games = game_service.get_games_for_user(db, current_user, active_only=True)
    return JSONResponse (
        status_code=status.HTTP_200_OK,
        content={"games": games}
    )

@router.get("/")
def get_all_games_for_user(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_factory()),
    ):
    games = game_service.get_games_for_user(db, current_user, active_only=False)
    return JSONResponse (
        status_code=status.HTTP_200_OK,
        content={"games": games}
    )

@router.get("/{id}", status_code=status.HTTP_200_OK, response_model=GameDetailOutputModel)
def get_game_details_from_id(
    id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_factory()),
    ):
    game = game_service.get_game_details_from_id(db, current_user, id)
    return game

@router.post("/{id}/answers")
def post_answers_for_game(
    id: int,
    answer_model: AnswerInputModel,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_factory()),
    ):
    game, round_score_percentage = game_service.give_answers_for_game(
        db,
        current_user,
        id,
        answer_model.from_foreign_language,
        answer_model.from_your_language
    )
    return JSONResponse (
                status_code=status.HTTP_200_OK,
                content={
                    "game": game,
                    "round_score_percentage": round_score_percentage
                }
    )
