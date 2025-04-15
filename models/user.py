from datetime import datetime
from sqlalchemy import BigInteger, String, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base
import phonenumbers  # pip install phonenumbers
from pydantic import EmailStr, BaseModel  # pip install pydantic[email]


class Client(Base):
    """Модель клиента кредитной компании с защитой данных
    Основные поля:
    clientID            --- Integer, primary_key, autoincrement
    fullName            --- String(100),nullable
    passport            --- String(20), unique, nullable
    telegram_id         --- BigInteger, unique, nullable
    phone_numbers       --- JSON, nullable
    email               --- String(100), unique, nullable
    registration_date   --- DateTime
    creditScore         --- Integer
    """
    __tablename__ = "clients"
    __table_args__ = {
        'comment': 'Таблица клиентов кредитной организации'
    }

    # Основные поля
    clientID: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True,
        comment="Уникальный внутренний ID клиента"
    )
    fullName: Mapped[str] = mapped_column(String(100),nullable=False,
        comment="Полное имя (фамилия, имя, отчество)"
    )
    passport: Mapped[str] = mapped_column(String(20),unique=True,nullable=False,
        comment="Серия и номер паспорта (зашифровано)"
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger,unique=True,nullable=True,
        comment="ID Telegram для уведомлений"
    )
    phone_numbers: Mapped[list[str]] = mapped_column(JSON,nullable=False,
        comment="Список телефонов в международном формате"
    )
    email: Mapped[str] = mapped_column(String(100),unique=True,nullable=True,
        comment="Контактный email (зашифровано)"
    )
    registration_date: Mapped[datetime] = mapped_column(DateTime,default=datetime.utcnow,
        comment="Дата регистрации клиента"
    )
    creditScore: Mapped[int] = mapped_column(Integer,default=0,
        comment="Кредитный рейтинг (0-1000)"
    )

    # Методы валидации
    @staticmethod
    def validate_phone(phone: str) -> str:
        """Приведение телефона к международному формату"""
        try:
            parsed = phonenumbers.parse(phone, None)
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError("Invalid phone number")
            return phonenumbers.format_number(
                parsed,
                phonenumbers.PhoneNumberFormat.E164
            )
        except Exception as e:
            raise ValueError(f"Phone validation failed: {str(e)}")

    # Схема для Pydantic (безопасный экспорт данных)
    class SafeSchema(BaseModel):
        clientID: int
        fullName: str
        telegram_id: int | None
        registration_date: datetime
        creditScore: int

        class Config:
            from_attributes = True

    def to_safe_schema(self) -> SafeSchema:
        """Возвращает безопасное представление данных"""
        return self.SafeSchema(
            clientID=self.clientID,
            fullName=self.fullName,
            telegram_id=self.telegram_id,
            registration_date=self.registration_date,
            creditScore=self.creditScore
        )

    def admin_view(self) -> str:
        """Полное представление для администратора"""
        return (
            f"ClientID: {self.clientID}\n"
            f"ФИО: {self.fullName}\n"
            f"Паспорт: [зашифровано]\n"
            f"Telegram: {self.telegram_id}\n"
            f"Телефон: {self.phone_numbers}\n"
            f"Email: {self.email}\n"
            f"Кредитный рейтинг: {self.creditScore}"
        )