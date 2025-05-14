from typing import List
from pydantic import BaseModel

class StatOutputModel(BaseModel):
    word: str
    translations: List[str]
    n_appearances: int
    n_correct_answers: int
    total_score_percent: float