def get_credit_status(score: int) -> str:
    """Возвращает текстовый статус в зависимости от рейтинга"""
    if score >= 800:
        return "Отличный - высокий приоритет одобрения"
    elif score >= 600:
        return "Хороший - стандартные условия"
    elif score >= 400:
        return "Удовлетворительный - повышенные ставки"
    else:
        return "Низкий - требуется дополнительная проверка"

def get_credit_advice(score: int) -> str:
    """Генерирует рекомендации для улучшения рейтинга"""
    advice = []
    if score < 700:
        advice.append("- Своевременно погашайте кредиты")
    if score < 500:
        advice.append("- Увеличьте частоту использования сервиса")
    if score < 300:
        advice.append("- Обратитесь в отделение для консультации")

    return "\n".join(advice) if advice else "Ваш рейтинг оптимальный!"