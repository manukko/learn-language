from typing import List
from pydantic import BaseModel

class StatOutputModel(BaseModel):
    """
    Represents statistical information about a word and its translations.

    Attributes:
        word (str): The word being analyzed.
        translations (List[str]): List of translations for the word.
        n_appearances (int): Number of times the word has appeared.
        n_correct_answers (int): Number of times the word was answered correctly.
        total_score_percent (float): Percentage score based on correct answers.
    """
    word: str
    translations: List[str]
    n_appearances: int
    n_correct_answers: int
    total_score_percent: float