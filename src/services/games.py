from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from src.db.models import Stat, User, Word, Game, GameWord, SUPPORTED_LANGUAGES, WordTranslation
import random
from src.schemas.games import GameOutputModel, GameDetailOutputModel
from typing import List, Tuple
from src.utils import calculate_score_percentage

class GameService:
    def __init__(self):
        self.MAX_OPENED_GAMES_FOR_USER = 10
        self.MAX_WORD_SCORE_HARD_GAME = 0.5 #50%
        self.MIN_WORD_SCORE_RECAP_GAME = 0.5

    def create_new_game(
        self,
        db: Session,
        user: User,
        language: str,
        n_words_to_guess: int,
        n_vocabulary: int,
        type: str
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

        words = []
        n_words_to_guess = min(n_words_to_guess, n_vocabulary)  # n_words_to_guess <= n_vocabulary

        if type == "hard":
            stats = (
                db.query(Stat)
                    .join(Stat.word)
                    .filter(Word.language == language)
                    .filter(Stat.user_id == user.id)
                    .filter((Stat.n_correct_answers / Stat.n_appearances) <= self.MAX_WORD_SCORE_HARD_GAME)
                    .order_by(text('RANDOM()'))
                    .limit(n_words_to_guess)
                    .all()
            )
            words = [stat.word for stat in stats]
        elif type == "recap":
            stats = (
                db.query(Stat)
                    .join(Stat.word)
                    .filter(Word.language == language)
                    .filter(Stat.user_id == user.id)
                    .filter((Stat.n_correct_answers / Stat.n_appearances) >= self.MIN_WORD_SCORE_RECAP_GAME)
                    .order_by(text('RANDOM()'))
                    .limit(n_words_to_guess)
                    .all()
            )
            words = [stat.word for stat in stats]

        n_missing_words = n_words_to_guess-len(words)
        if n_missing_words > 0:
            words_translations = (
                db.query(WordTranslation)
                    .join(WordTranslation.word)
                    .filter(Word.language == language)
                    .order_by(WordTranslation.frequency)
                    .limit(n_vocabulary)
                    .all()
            )
            vocabulary = [word_translation.word for word_translation in words_translations]
            n_vocabulary = len(vocabulary)  # n_vocabulary might be less than number provided by user
            random.shuffle(vocabulary)
            if n_missing_words > 0:
                words.extend(vocabulary[0:n_missing_words])
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
            new_game_word = GameWord(game_id=new_game.id, word_id=word.id)
            db.add(new_game_word)
        db.commit()
        return new_game, words
    
    def get_games_for_user(self, db: Session, user: User, active_only: bool) -> List[GameOutputModel]:

        games = db.query(Game).filter(Game.user_id == user.id)
        if active_only:
            games = games.filter(Game.is_active)
        games = games.all()
        games = [
            GameOutputModel.model_validate(game).model_dump() for game in games
        ]
        return games
    
    def get_game_details_from_id(self, db: Session, user: User, game_id: int) -> GameDetailOutputModel:

        game = db.query(Game).filter(Game.user_id == user.id).filter(Game.id == game_id).first()
        if not game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No game of yours corresponds to the id provided!"
            )
        n_remaining_words_to_guess = [word.word.text for word in game.words]
        n_remaining_words_to_guess_number=len(n_remaining_words_to_guess)
        if n_remaining_words_to_guess_number==game.n_words_to_guess:
            game_score_percentage = None
        else:
            game_score_percentage = game.n_correct_answers / (game.n_words_to_guess - n_remaining_words_to_guess_number)
        
        print(f"is_active={game.is_active}")
        game_output_model = GameDetailOutputModel(
            id=game.id,
            language=game.language,
            n_words_to_guess=game.n_words_to_guess,
            n_vocabulary=game.n_vocabulary,
            n_correct_answers=game.n_correct_answers,
            n_remaining_words_to_guess=n_remaining_words_to_guess_number,
            game_score_percentage=game_score_percentage,
            remaining_words_to_guess=n_remaining_words_to_guess,
        ).model_dump()
        return game_output_model

    def give_answers_for_game(
        self, db: Session, user: User, game_id: int, answers: dict[str, str]
    ) -> Tuple[GameDetailOutputModel, float]:
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
        
        remaining_game_words_to_guess_dict: dict[str, GameWord] = {}
        game_words: List[GameWord] = game.words
        for game_word in game_words:
            remaining_game_words_to_guess_dict[game_word.word.text] = game_word
        
        n_round_valid_attempts = 0
        n_round_correct_answers = 0

        for word_text, word_candidate_translation_text in answers.items():
            word_text = word_text.lower()
            word_candidate_translation_text = word_candidate_translation_text.lower()
            if word_text in list(remaining_game_words_to_guess_dict.keys()):
                game_word = remaining_game_words_to_guess_dict[word_text]
                word = game_word.word
                n_round_valid_attempts += 1
                word_translations_gt: List[str] = [word_translation.translation.text for word_translation in word.translations]
                if word_candidate_translation_text in word_translations_gt:
                    correct_answer_increment = 1
                    n_round_correct_answers += 1
                else:
                    correct_answer_increment = 0
                remaining_game_words_to_guess_dict.pop(word_text)
                db.delete(game_word)
                stat = db.query(Stat).filter(Stat.user_id == user.id).filter(Stat.word_id == word.id).first()
                if not stat:
                    db.add(
                        Stat(
                            user_id=user.id,
                            word_id=word.id,
                            n_appearances=1,
                            n_correct_answers=correct_answer_increment,
                        )
                    )
                else:
                    stat.n_appearances += 1
                    stat.n_correct_answers += correct_answer_increment
                db.commit()
        
        game.n_correct_answers = game.n_correct_answers + n_round_correct_answers
        round_score_percentage = calculate_score_percentage(n_round_correct_answers, n_round_valid_attempts)

        remaining_words_to_guess = list(remaining_game_words_to_guess_dict.keys())
        n_remaining_words_to_guess = len(remaining_words_to_guess)
        
        if n_remaining_words_to_guess == 0:
            game.is_active = False

        db.commit()
        db.refresh(game)

        n_game_answers = game.n_words_to_guess - n_remaining_words_to_guess
        game_score_percentage = calculate_score_percentage(game.n_correct_answers, n_game_answers)
        
        game = GameDetailOutputModel(
            id=game.id,
            language=game.language,
            n_words_to_guess=game.n_words_to_guess,
            n_vocabulary=game.n_vocabulary,
            n_correct_answers=game.n_correct_answers,
            n_remaining_words_to_guess=n_remaining_words_to_guess,
            game_score_percentage=game_score_percentage,
            remaining_words_to_guess=remaining_words_to_guess,
        ).model_dump()
        return game, round_score_percentage