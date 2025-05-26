from typing import List, Literal
from pydantic import BaseModel, Field


class GameOutputModel(BaseModel):
    """
    GameOutputModel represents the output schema for a game instance.

    Attributes:
        id (int): Unique identifier for the game.
        language (str): The language associated with the game.
        n_words_to_guess (int): Number of words to guess in the game. Must be at least 1.
        n_vocabulary (int): Total number of vocabulary words available in the game. Must be at least 50.

    Config:
        model_config (dict): Configuration for the model, enabling attribute-based initialization.
    """
    id: int
    language: str
    n_words_to_guess: int = Field(..., ge=1)
    n_vocabulary: int = Field(..., ge=1)
    model_config = {
        "from_attributes": True
    }

class GameDetailOutputModel(GameOutputModel):
    """
    Represents detailed information about a game session.

    Attributes:
        n_correct_answers (int): The number of correct answers given by the player.
        n_remaining_words_to_guess (int): The total number of words left to guess in the game.
        from_foreign_language (List[str]): The list of remaining words you have to translate from foreign language to yours.
        from_your_language (List[str]): A list of remaining words you have to translate from your language to foreign.
        game_score_percentage (float | None): The player's score as a percentage, or None if not applicable.
    """
    n_correct_answers: int
    n_remaining_words_to_guess: int
    from_foreign_language: List[str]
    from_your_language: List[str]
    game_score_percentage: float | None

class GameCreateInputModel(BaseModel):
    """
    Input model for creating a new game.

    Attributes:
        language (str): The language in which the game will be played.
        n_vocabulary (int): The number of vocabulary words available for the game.
        n_words_to_guess (int, optional): The number of words the player needs to guess. Defaults to 10.
        type (str, optional): The type of game to create between:
        - random (default): choose words randomly on n_vocabulary most frequent words in foreign language
        - hard: choose words among the ones with score <= 50% (if not enough words with stats, choose the others as in mode 'random')
        - recap: choose words among the ones with score >= 50% (if not enough words with stats, choose the others as in mode 'random')
        translate_from_your_language_percentage (str, optional): percentage of words to translate from your language to foreign language; \
            100 - translate_to_your_language_percentage is the percentage of words to translate from foreign language to your language instead.
    """
    language: str
    n_vocabulary: int
    n_words_to_guess: int = 10
    type: Literal['random', 'hard', 'recap'] = 'random'
    translate_from_your_language_percentage: int = Field(default=0, ge=0, le=100)

class AnswerInputModel(BaseModel):
    """
    Model representing the input for an answer in a language learning game.

    Attributes:
        from_foreign_language (dict[str, str]): 
            A dictionary mapping words in the foreign language to their translations.
        from_your_language (dict[str, str]): 
            A dictionary mapping words in the user's native language to their translations.
    """
    from_foreign_language: dict[str, str] = {}
    from_your_language: dict[str, str] = {}