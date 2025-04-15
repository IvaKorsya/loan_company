import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException

def validate_phone_number(raw_phone: str) -> str:
    """Валидация и нормализация номера телефона"""
    try:
        parsed = phonenumbers.parse(raw_phone, "RU")
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError("Неверный номер телефона")
        return phonenumbers.format_number(
            parsed,
            phonenumbers.PhoneNumberFormat.E164
        )
    except NumberParseException:
        raise ValueError("Введите номер в формате +7XXXYYYYYYY")