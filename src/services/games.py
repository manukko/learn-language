from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from src.db.models import Stat, User, Word, Game, GameWords, SUPPORTED_LANGUAGES, WordTranslation
import random
from src.schemas.games import GameOutputModel, GameDetailOutputModel, StatOutputModel
from typing import List, Tuple
from src.utils import calculate_score_percentage


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
        n_remaining_words_to_guess = [word.word.source_word for word in game.words]
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
            n_remaining_words_to_guess_number=n_remaining_words_to_guess_number,
            game_score_percentage=game_score_percentage,
            n_remaining_words_to_guess=n_remaining_words_to_guess,
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
        
        remaining_words_to_guess = [word.word.source_word for word in game.words]
        language = game.language
        n_round_valid_attempts = 0
        n_round_correct_answers = 0

        for source_word, word_candidate_translation in answers.items():
            source_word = source_word.lower()
            word_candidate_translation = word_candidate_translation.lower()
            if source_word in remaining_words_to_guess:
                n_round_valid_attempts += 1
                word_gt = db.query(Word).filter(Word.language == language).filter(Word.source_word == source_word).first()
                translations_gt: List[str] = [word_translation.translation for word_translation in word_gt.translations]
                print(translations_gt)
                if word_candidate_translation in translations_gt:
                    correct_answer_increment = 1
                    n_round_correct_answers += 1
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
        
        game.n_correct_answers = game.n_correct_answers + n_round_correct_answers
        round_score_percentage = calculate_score_percentage(n_round_correct_answers, n_round_valid_attempts)

        if n_round_valid_attempts == len(remaining_words_to_guess):
            game.is_active = False

        db.commit()
        db.refresh(game)

        remaining_words_to_guess = [game_word.word.source_word for game_word in game.words]
        n_remaining_words_to_guess = len(remaining_words_to_guess)
        n_game_answers = game.n_words_to_guess - n_remaining_words_to_guess
        game_score_percentage = calculate_score_percentage(game.n_correct_answers, n_game_answers)
        
        game = GameDetailOutputModel(
            id=game.id,
            language=game.language,
            n_words_to_guess=game.n_words_to_guess,
            n_vocabulary=game.n_vocabulary,
            n_correct_answers=game.n_correct_answers,
            n_remaining_words_to_guess_number=n_remaining_words_to_guess,
            game_score_percentage=game_score_percentage,
            n_remaining_words_to_guess=remaining_words_to_guess,
        ).model_dump()
        return game, round_score_percentage

    def get_stats_for_user(self, db: Session, user: User) -> List[StatOutputModel]:
        stats = db.query(Stat).filter(Stat.user_id == user.id).all()
        stats_output_model = []
        for stat in stats:
            stat_output_model = StatOutputModel(
                word=stat.word.source_word,
                translations=[word_translation.translation for word_translation in stat.word.translations],
                n_appearances=stat.n_appearances,
                n_correct_answers=stat.n_correct_answers,
                total_score_percent=calculate_score_percentage(stat.n_correct_answers,stat.n_appearances)
            )
            stats_output_model.append(stat_output_model)
        stats_output_model.sort(key=lambda x: (x.total_score_percent, -x.n_appearances))
        return stats_output_model