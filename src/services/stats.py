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
            stats_query = stats_query.join(Stat.word).filter(Stat.language == language)
            # order by: foreign->user language translations before user->foreign, then stat score asc, then alphabetical order asc
            stats_query = stats_query.order_by(Word.language != language, Stat.n_correct_answers / Stat.n_appearances, Word.text)
        stats = stats_query.all()
        print(stats)
        stats_output_model = []
        for stat in stats:
            if stat.language == stat.word.language:
                translations=[word_translation.translation.text for word_translation in stat.word.associated_translations]
            else:
                translations=[translation_words.word.text for translation_words in stat.word.associated_words]
            stat_output_model = StatOutputModel(
                word=stat.word.text,
                translations=translations,
                language=stat.language,
                word_language=stat.word.language,
                n_appearances=stat.n_appearances,
                n_correct_answers=stat.n_correct_answers,
                total_score_percent=calculate_score_percentage(stat.n_correct_answers,stat.n_appearances)
            )
            stats_output_model.append(stat_output_model)
        return stats_output_model