from typing import List
from pydantic import BaseModel


class GameModel(BaseModel):
    id: int
    language: str
    total_words_to_guess: int
    vocabulary_size: int
    model_config = {
        "from_attributes": True
    }

class GameDetailModel(GameModel):
    correct_words_number: int
    remaining_words_to_guess_number: int
    remaining_words_to_guess: List[str]
    score_percentage: int | None

class GameCreate(BaseModel):
    language: str
    vocabulary_size: int
    total_words_to_guess: int = 10

class AnswerModel(BaseModel):
    answers: dict[str, str]