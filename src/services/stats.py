from sqlalchemy.orm import Session
from src.db.models import Stat, User
from src.schemas.stats import StatOutputModel
from typing import List
from src.utils import calculate_score_percentage


class StatService:
    def __init__(self):
        pass

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