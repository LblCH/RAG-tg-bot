import re

def is_valid_query(text: str) -> bool:
    if not text or len(text.strip()) < 5:
        return False

    text = text.strip()

    # Отклоняем команды /reset, /version, и т.п.
    if text.startswith("/"):
        return False

    # Если нет ни одной буквы (только цифры или символы) — не валидно
    if not re.search(r"[а-яА-Яa-zA-Z]", text):
        return False

    # Если состоит только из знаков препинания или мусора
    if re.fullmatch(r"[^\w\s]+", text):
        return False

    # Если только одно короткое слово (менее 4 букв)
    if len(text.split()) == 1 and len(text) <= 4:
        return False

    return True
