from sqlalchemy.orm import Session
from src.db.models import Stat, User, Word
from src.schemas.stats import StatOutputModel
from typing import List
from src.utils import calculate_score_percentage


class StatService:
    def __init__(self):
        pass

    def get_stats_for_user(self, db: Session, user: User, language) -> List[StatOutputModel]:
        stats_query = db.query(Stat).filter(Stat.user_id == user.id)
        if language:
            stats_query = stats_query.join(Stat.word).filter(Word.language == language)
        stats = stats_query.all()
        stats_output_model = []
        for stat in stats:
            stat_output_model = StatOutputModel(
                language=stat.word.language,
                word=stat.word.text,
                translations=[word_translation.translation.text for word_translation in stat.word.associated_translations],
                n_appearances=stat.n_appearances,
                n_correct_answers=stat.n_correct_answers,
                total_score_percent=calculate_score_percentage(stat.n_correct_answers,stat.n_appearances)
            )
            stats_output_model.append(stat_output_model)
        stats_output_model.sort(key=lambda x: (x.total_score_percent, -x.n_appearances))
        return stats_output_model