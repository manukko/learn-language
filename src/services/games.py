from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from src.db.models import Stat, User, Word, Game, GameWord, SUPPORTED_LANGUAGES, USER_LANGUAGE, WordTranslation
import random
from src.schemas.games import GameOutputModel, GameDetailOutputModel
from typing import List, Tuple
from src.utils import calculate_score_percentage

class GameService:
    def __init__(self):
        self.MAX_OPENED_GAMES_FOR_USER = 10
        self.MAX_WORD_SCORE_HARD_GAME = 0.5 #50%
        self.MIN_WORD_SCORE_RECAP_GAME = 0.5

    def _generate_words_for_new_game(
        self,
        db: Session,
        user: User,
        language: str,
        n_words_to_guess: int,
        n_vocabulary: int,
        game_type: str,
        translate_from_your_language_percentage: int
    ):
        words = []
        vocabulary = []
        n_words_to_guess = min(n_words_to_guess, n_vocabulary)  # n_words_to_guess <= n_vocabulary
        n_words_translate_from_your_language = int(n_words_to_guess * translate_from_your_language_percentage / 100)
        n_words_translate_from_target_language = n_words_to_guess - n_words_translate_from_your_language

        if game_type == "hard":
            stats = (
                db.query(Stat)
                    .filter(Stat.language == language)
                    .filter(Stat.user_id == user.id)
                    .filter((Stat.n_correct_answers / Stat.n_appearances) <= self.MAX_WORD_SCORE_HARD_GAME)
                    .join(Stat.word)
                    .filter(Word.language != language)
                    .order_by(text('RANDOM()'))
                    .limit(n_words_translate_from_your_language)
                    .all()
            )
            words_translate_from_your_language = [stat.word for stat in stats]
            n_words_translate_from_your_language -= len(words_translate_from_your_language)
            stats = (
                db.query(Stat)
                    .filter(Stat.language == language)
                    .filter(Stat.user_id == user.id)
                    .filter((Stat.n_correct_answers / Stat.n_appearances) <= self.MAX_WORD_SCORE_HARD_GAME)
                    .join(Stat.word)
                    .filter(Word.language == language)
                    .order_by(text('RANDOM()'))
                    .limit(n_words_translate_from_target_language)
                    .all()
            )
            words_translate_from_target_language = [stat.word for stat in stats]
            n_words_translate_from_target_language -= len(words_translate_from_target_language)

            words = words_translate_from_your_language + words_translate_from_target_language

        elif game_type == "recap":
            stats = (
                db.query(Stat)
                    .filter(Stat.language == language)
                    .filter(Stat.user_id == user.id)
                    .filter((Stat.n_correct_answers / Stat.n_appearances) >= self.MIN_WORD_SCORE_RECAP_GAME)
                    .join(Stat.word)
                    .filter(Word.language != language)
                    .order_by(text('RANDOM()'))
                    .limit(n_words_translate_from_your_language)
                    .all()
            )
            words_translate_from_your_language = [stat.word for stat in stats]
            n_words_translate_from_your_language -= len(words_translate_from_your_language)
            stats = (
                db.query(Stat)
                    .filter(Stat.language == language)
                    .filter(Stat.user_id == user.id)
                    .filter((Stat.n_correct_answers / Stat.n_appearances) >= self.MIN_WORD_SCORE_RECAP_GAME)
                    .join(Stat.word)
                    .filter(Word.language == language)
                    .order_by(text('RANDOM()'))
                    .limit(n_words_translate_from_target_language)
                    .all()
            )
            words_translate_from_target_language = [stat.word for stat in stats]
            n_words_translate_from_target_language -= len(words_translate_from_target_language)

            words = words_translate_from_your_language + words_translate_from_target_language

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
            if n_words_translate_from_target_language > 0:
                vocabulary = [word_translation.word for word_translation in words_translations]
                n_vocabulary_gt = len(vocabulary)
                random.shuffle(vocabulary)
                words.extend(vocabulary[0:n_words_translate_from_target_language])
            if n_words_translate_from_your_language > 0:
                vocabulary = [word_translation.translation for word_translation in words_translations]
                random.shuffle(vocabulary)
                if n_missing_words > 0:
                    words.extend(vocabulary[0:n_words_translate_from_your_language])

        n_words_to_guess_gt = len(words) # n_words_to_guess_gt might be less than number provided by user
        n_vocabulary_gt = max(len(vocabulary), n_words_to_guess_gt)   # n_vocabulary_gt might be less than number provided by user
        random.shuffle(words)
        return words, n_vocabulary_gt, n_words_to_guess_gt

    def create_new_game(
        self,
        db: Session,
        user: User,
        language: str,
        n_words_to_guess: int,
        n_vocabulary: int,
        game_type: str,
        translate_from_your_language_percentage: int
    ) -> GameDetailOutputModel:
        
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

        words, n_vocabulary_gt, n_words_to_guess_gt  = self._generate_words_for_new_game(
            db,
            user,
            language,
            n_words_to_guess,
            n_vocabulary,
            game_type,
            translate_from_your_language_percentage
        )

        new_game = Game(
            user_id=user.id,
            language=language,
            n_words_to_guess=n_words_to_guess_gt,
            n_vocabulary=n_vocabulary_gt,
        )
        db.add(new_game)
        db.commit()
        db.refresh(new_game)
        for word in words:
            new_game_word = GameWord(game_id=new_game.id, word_id=word.id)
            db.add(new_game_word)
        db.commit()

        game_detail_output_detail = GameDetailOutputModel(
            id=new_game.id,
            language=new_game.language,
            n_words_to_guess=n_words_to_guess_gt,
            n_vocabulary=n_vocabulary_gt,
            n_correct_answers=new_game.n_correct_answers,
            n_remaining_words_to_guess=new_game.n_words_to_guess,
            from_target_language=[word.text for word in words if word.language == language],
            from_your_language=[word.text for word in words if word.language != language],
            game_score_percentage=None
        ).model_dump()
        return game_detail_output_detail
    
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
        words_to_guess = []
        words_to_guess_from_target_language = []
        words_to_guess_from_your_language = []
        for game_word in game.words:
            word_text = game_word.word.text
            words_to_guess.append(word_text)
            if game_word.word.language == game.language:
                words_to_guess_from_target_language.append(word_text)
            else:
                words_to_guess_from_your_language.append(word_text)
        n_words_to_guess=len(words_to_guess)

        if n_words_to_guess==game.n_words_to_guess:
            game_score_percentage = None
        else:
            game_score_percentage = game.n_correct_answers / (game.n_words_to_guess - n_words_to_guess)
        
        game_output_model = GameDetailOutputModel(
            id=game.id,
            language=game.language,
            n_words_to_guess=game.n_words_to_guess,
            n_vocabulary=game.n_vocabulary,
            n_correct_answers=game.n_correct_answers,
            n_remaining_words_to_guess=n_words_to_guess,
            game_score_percentage=game_score_percentage,
            from_target_language=words_to_guess_from_target_language,
            from_your_language=words_to_guess_from_your_language
        ).model_dump()
        return game_output_model

    def give_answers_for_game(
        self,
        db: Session,
        user: User,
        game_id: int,
        from_target_language_translation_candidates: dict[str, str],
        from_your_language_translation_candidates: dict[str, str]
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
        
        from_target_language_gamewords_dict: dict[str, GameWord] = {}
        from_your_language_gamewords_dict: dict[str, GameWord] = {}
        game_words: List[GameWord] = game.words
        for game_word in game_words:
            if game_word.word.language == game.language:
                from_target_language_gamewords_dict[game_word.word.text] = game_word
            else:
                from_your_language_gamewords_dict[game_word.word.text] = game_word

        n_from_target_language_valid_attemps, n_from_target_language_correct_answers = self._verify_answers(
            db,
            user,
            game,
            from_target_language_translation_candidates,
            from_target_language_gamewords_dict,
        )
        n_from_your_language_valid_attemps, n_from_your_language_correct_answers = self._verify_answers(
            db,
            user,
            game,
            from_your_language_translation_candidates,
            from_your_language_gamewords_dict,
        )

        n_valid_attempts = n_from_target_language_valid_attemps + n_from_your_language_valid_attemps
        n_correct_answers = n_from_target_language_correct_answers + n_from_your_language_correct_answers
        round_score_percentage = calculate_score_percentage(n_correct_answers, n_valid_attempts)

        remaining_words_to_guess_from_target_language = [
            game_word.word.text
            for game_word in from_target_language_gamewords_dict.values()
            if game_word.word.language == game.language
        ]
        remaining_words_to_guess_from_your_language = [
            game_word.word.text
            for game_word in from_your_language_gamewords_dict.values()
            if game_word.word.language != game.language
        ]
        n_remaining_words_to_guess = len(remaining_words_to_guess_from_target_language) + len(remaining_words_to_guess_from_your_language)
    
        game.n_correct_answers = game.n_correct_answers + n_correct_answers
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
            from_target_language=remaining_words_to_guess_from_target_language,
            from_your_language=remaining_words_to_guess_from_your_language,
        ).model_dump()
        return game, round_score_percentage

    def _verify_answers(
        self,
        db: Session,
        user: User,
        game: Game,
        answers: dict[str, str],
        solutions: dict[str, GameWord]
    ):
        n_valid_attempts = 0
        n_correct_answers = 0

        for word_text, word_candidate_translation_text in answers.items():
            word_text = word_text.lower()
            word_candidate_translation_text = word_candidate_translation_text.lower()
            if word_text in list(solutions.keys()):
                game_word = solutions[word_text]
                word = game_word.word
                n_valid_attempts += 1
                if game.language == word.language:
                    correct_solutions_gt: List[str] = [
                        word_translation.translation.text
                        for word_translation in word.associated_translations
                        if word_translation.translation.language == USER_LANGUAGE
                    ]
                else:
                    # if word is not in game language, it is to translate in game language
                    # then the possible solutions are all words in game language associated with that translation
                    correct_solutions_gt: List[str] = [
                        translation_word.word.text
                        for translation_word in word.associated_words
                        if translation_word.translation.language == game.language

                    ]
                if word_candidate_translation_text in correct_solutions_gt:
                    correct_answer_increment = 1
                    n_correct_answers += 1
                else:
                    correct_answer_increment = 0
                solutions.pop(word_text)
                db.delete(game_word)
                stat = db.query(Stat).filter(Stat.user_id == user.id).filter(Stat.word_id == word.id).first()
                if not stat:
                    db.add(
                        Stat(
                            user_id=user.id,
                            word_id=word.id,
                            language=game.language,
                            n_appearances=1,
                            n_correct_answers=correct_answer_increment,
                        )
                    )
                else:
                    stat.n_appearances += 1
                    stat.n_correct_answers += correct_answer_increment
                db.commit()
        
        return n_valid_attempts, n_correct_answers