from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from src.db.models import Stat, User, Word, Game, GameWords, SUPPORTED_LANGUAGES
import random
from src.schemas.games import GameModel, GameDetailModel
from typing import List, Tuple


class GameService:
    def __init__(self):
        self.MAX_OPENED_GAMES_FOR_USER = 10

    def create_new_game(
        self,
        db: Session,
        user: User,
        language: str,
        n_words_to_guess: int,
        n_vocabulary: int
    ) -> Tuple[Game, List[Word]]:
        
        if language not in SUPPORTED_LANGUAGES:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Language is not supported.",
            )
        n_active_games = len([game for game in user.games if game.is_active])
        if n_active_games >= self.MAX_OPENED_GAMES_FOR_USER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="""
                You have reached the limit of opened games.
                Please finish some opened games before opening a new one.
                """,
            )

        vocabulary = (
            db.query(Word).order_by(Word.frequency).limit(n_vocabulary).all()
        )
        n_vocabulary = len(vocabulary)  # n_vocabulary might be less than number provided by user
        n_words_to_guess = min(n_words_to_guess, n_vocabulary)  # n_words_to_guess <= n_vocabulary
        random.shuffle(vocabulary)
        words = vocabulary[0:n_words_to_guess]
        new_game = Game(
            user_id=user.id,
            language=language,
            n_words_to_guess=n_words_to_guess,
            n_vocabulary=n_vocabulary,
        )
        db.add(new_game)
        db.commit()
        db.refresh(new_game)
        for word in words:
            new_game_word = GameWords(game_id=new_game.id, word_id=word.id)
            db.add(new_game_word)
        db.commit()
        return new_game, words
    
    def get_games_for_user(self, db: Session, user: User, active_only: bool) -> List[GameModel]:

        games = db.query(Game).filter(User.username == user.username)
        if active_only:
            games.filter(Game.is_active)
        games = games.all()
        games = [
            GameModel.model_validate(game).model_dump() for game in games
        ]
        return games
    
    def get_game_details_from_id(self, db: Session, user: User, game_id: int) -> GameDetailModel:

        game = db.query(Game).filter(User.username == user.username).filter(Game.id == game_id).first()
        if not game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No game of yours corresponds to the id provided!"
            )
        n_remaining_words_to_guess = [word.word.name for word in game.words]
        n_remaining_words_to_guess_number=len(n_remaining_words_to_guess)
        if n_remaining_words_to_guess_number==game.n_words_to_guess:
            game_score_percentage = None
        else:
            game_score_percentage = game.n_correct_answers / (game.n_words_to_guess - n_remaining_words_to_guess_number)
        game = GameDetailModel(
            id=game.id,
            language=game.language,
            n_words_to_guess=game.n_words_to_guess,
            n_vocabulary=game.n_vocabulary,
            n_correct_answers=game.n_correct_answers,
            n_remaining_words_to_guess_number=n_remaining_words_to_guess_number,
            game_score_percentage=game_score_percentage,
            n_remaining_words_to_guess=n_remaining_words_to_guess,
        ).model_dump()
        return game

    def give_answers_for_game(
        self, db: Session, user: User, game_id: int, answers: dict[str, str]
    ) -> Tuple[GameDetailModel, float]:
        game = db.query(Game).filter(Game.user_id == user.id) \
            .filter(Game.id == game_id).first()
        if not game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No game of yours corresponds to the id provided!"
            )
        if not game.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Game has ended, please play an active game!"
            )
        
        n_remaining_words_to_guess = [word.word.name for word in game.words]
        language = game.language
        total_attempts = 0
        n_correct_answers = 0

        for word_name, word_candidate_translation in answers.items():
            word_name = word_name.lower()
            word_candidate_translation = word_candidate_translation.lower()
            if word_name in n_remaining_words_to_guess:
                total_attempts += 1
                word_gt = db.query(Word).filter(Word.language == language).filter(Word.name == word_name).first()
                translation_gt = word_gt.translation
                if translation_gt == word_candidate_translation:
                    correct_answer_increment = 1
                    n_correct_answers += 1
                else:
                    correct_answer_increment = 0
                db.query(GameWords).filter(GameWords.game_id == game.id). \
                    filter(GameWords.word_id == word_gt.id).delete()
                stat = db.query(Stat).filter(Stat.user_id == user.id).filter(Stat.word_id == word_gt.id).first()
                if not stat:
                    db.add(
                        Stat(
                            user_id=user.id,
                            word_id=word_gt.id,
                            n_appearances=1,
                            n_correct_answers=correct_answer_increment,
                        )
                    )
                else:
                    stat.n_correct_answers += 1
                    stat.n_correct_answers += correct_answer_increment
                db.commit()
        
        game.n_correct_answers = game.n_correct_answers + n_correct_answers
        round_score_percentage = (
            round(n_correct_answers * 100 / total_attempts, 2)
            if total_attempts > 0
            else None
        )

        if total_attempts == len(n_remaining_words_to_guess):
            game.is_active = False

        db.commit()
        db.refresh(game)
        n_remaining_words_to_guess = [word.word.name for word in game.words]
        n_remaining_words_to_guess_number = len(n_remaining_words_to_guess)
        game_score_percentage = (
            round(
                game.n_correct_answers
                * 100
                / (game.n_words_to_guess - n_remaining_words_to_guess_number),
                2,
            )
            if game.n_words_to_guess > n_remaining_words_to_guess_number
            else None
        )
        
        game = GameDetailModel(
            id=game.id,
            language=game.language,
            n_words_to_guess=game.n_words_to_guess,
            n_vocabulary=game.n_vocabulary,
            n_correct_answers=game.n_correct_answers,
            n_remaining_words_to_guess_number=n_remaining_words_to_guess_number,
            game_score_percentage=game_score_percentage,
            n_remaining_words_to_guess=n_remaining_words_to_guess,
        ).model_dump()
        return game, round_score_percentage