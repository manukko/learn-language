from typing import List
from pydantic import BaseModel

class StatOutputModel(BaseModel):
    """
    Represents statistical information about a word and its translations.

    Attributes:
        word (str): The word being analyzed.
        translations (List[str]): List of translations for the word.
        language (str): The language of the translations.
        word_language (str): The language of the Stat: can be equal to the language or \
            to the user language if stat is for a translation from user language to foreign.
        n_appearances (int): Number of times the word has appeared.
        n_correct_answers (int): Number of times the word was answered correctly.
        total_score_percent (float): Percentage score based on correct answers.
    """
    word: str
    translations: List[str]
    language: str
    word_language: str
    n_appearances: int
    n_correct_answers: int
    total_score_percent: float