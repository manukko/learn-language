from typing import List
from pydantic import BaseModel, Field


class GameOutputModel(BaseModel):
    id: int
    language: str
    n_words_to_guess: int = Field(..., ge=1)
    n_vocabulary: int = Field(..., ge=50)
    model_config = {
        "from_attributes": True
    }

class GameDetailOutputModel(GameOutputModel):
    n_correct_answers: int
    n_remaining_words_to_guess_number: int
    n_remaining_words_to_guess: List[str]
    game_score_percentage: float | None

class GameCreateInputModel(BaseModel):
    language: str
    n_vocabulary: int
    n_words_to_guess: int = 10
    type: str = "random"

class AnswerInputModel(BaseModel):
    answers: dict[str, str]