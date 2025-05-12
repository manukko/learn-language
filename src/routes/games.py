from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from src.auth.auth import (
    get_db_session,
    get_current_user_factory
)
from src.db.models import User, Word, Game, GameWords, SUPPORTED_LANGUAGES
from src.schemas.games import GameCreate
import random
from src.schemas.games import GameModel, GameDetailModel, AnswerModel
router = APIRouter()

MAX_OPENED_GAMES_FOR_USER = 10

@router.post("/new")
def create_game(
    game_create_model: GameCreate,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_factory()),
    ):

    language = game_create_model.language.lower()
    total_words_to_guess = game_create_model.total_words_to_guess
    vocabulary_size = game_create_model.vocabulary_size

    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Language is not supported."
        )
    if len(current_user.games) >= MAX_OPENED_GAMES_FOR_USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=
            '''
            You have reached the limit of opened games.
            Please finish some opened games before opening a new one.
            '''       
        )

    vocabulary = db.query(Word).order_by(Word.frequency).limit(vocabulary_size).all()
    vocabulary_size = len(vocabulary) # vocabulary_size might be less than number provided by user
    total_words_to_guess = min(total_words_to_guess, vocabulary_size) # total_words_to_guess <= vocabulary_size
    random.shuffle(vocabulary)
    words = vocabulary[0:total_words_to_guess]

    new_game = Game(
        user_id=current_user.id,
        language=language,
        total_words_to_guess=total_words_to_guess,
        vocabulary_size=vocabulary_size
    )

    db.add(new_game)
    db.commit()
    db.refresh(new_game)

    for word in words:
        new_game_word = GameWords(
            game_id = new_game.id,
            word_id = word.id
        )
        db.add(new_game_word)
    db.commit()

    return JSONResponse (
        status_code=status.HTTP_200_OK,
        content={
            "detail": "game created successfully",
            "words": [game_word.name for game_word in words]
        }
    )

@router.get("/")
def get_active_games(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_factory()),
    ):
    games = db.query(Game).filter(Game.is_active).filter(User.username == current_user.username).all()
    games = [
        GameModel.model_validate(game).model_dump() for game in games
    ]
    return JSONResponse (
        status_code=status.HTTP_200_OK,
        content={"games": games}
    )

@router.get("/{id}")
def get_game(
    id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_factory()),
    ):
    game = db.query(Game).filter(User.username == current_user.username) \
        .filter(Game.id == id).first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No game of yours corresponds to the id provided!"
        )
    remaining_words_to_guess = [word.word.name for word in game.words]
    remaining_words_to_guess_number=len(remaining_words_to_guess)
    if remaining_words_to_guess_number==game.total_words_to_guess:
        score_percentage = None
    else:
        score_percentage = game.correct_words / (game.total_words_to_guess - remaining_words_to_guess_number)
    game = GameDetailModel(
        id=game.id,
        language=game.language,
        total_words_to_guess=game.total_words_to_guess,
        vocabulary_size=game.vocabulary_size,
        correct_words_number=game.correct_words,
        remaining_words_to_guess_number=remaining_words_to_guess_number,
        score_percentage=score_percentage,
        remaining_words_to_guess=remaining_words_to_guess,
    ).model_dump()
    print(game)
    return JSONResponse (
        status_code=status.HTTP_200_OK,
        content={"game": game}
    )

@router.post("/{id}/answers")
def post_answers_for_game(
    id: int,
    answer_model: AnswerModel,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_factory()),
    ):
    pass
'''
    game = db.query(Game).filter(User.username == current_user.username) \
        .filter(Game.id == id).first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No game of yours corresponds to the id provided!"
        )
    remaining_words_to_guess = [word.word.name for word in game.words]

    for key in answer_model.answers:
        if key not in remaining_words_to_guess:
            answer_model.answers.pop(key)
    
    return JSONResponse (
        status_code=status.HTTP_200_OK,
        content={"game": answer_model.answers}
    )
'''