from typing import List
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
        from_target_language (List[str]): The list of remaining words you have to translate from target language to yours.
        from_your_language (List[str]): A list of remaining words you have to translate from your language to target.
        game_score_percentage (float | None): The player's score as a percentage, or None if not applicable.
    """
    n_correct_answers: int
    n_remaining_words_to_guess: int
    from_target_language: List[str]
    from_your_language: List[str]
    game_score_percentage: float | None

class GameCreateInputModel(BaseModel):
    """
    Input model for creating a new game.

    Attributes:
        language (str): The language in which the game will be played.
        n_vocabulary (int): The number of vocabulary words available for the game.
        n_words_to_guess (int, optional): The number of words the player needs to guess. Defaults to 10.
        type (str, optional): The type of game to create. Defaults to "random".
        translate_from_your_language_percentage (str, optional): percentage of words to translate from your language to target language; \
            100 - translate_to_your_language_percentage is the percentage of words to translate from target language to your language instead.
    """
    language: str
    n_vocabulary: int
    n_words_to_guess: int = 10
    type: str = "random"
    translate_from_your_language_percentage: int = Field(default=0, ge=0, le=100)

class AnswerInputModel(BaseModel):
    """
    Input model for submitting answers in a game session.

    Attributes:
        answers (dict[str, str]): A mapping from question identifiers (or words) to the user's submitted answers.
    """
    answers: dict[str, str]