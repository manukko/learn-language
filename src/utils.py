
def calculate_score_percentage(n_correct_answers, n_total_answers):
    if n_total_answers > 0:
        game_score = n_correct_answers / n_total_answers
        return round(100*game_score, 2)
    else:
        return None