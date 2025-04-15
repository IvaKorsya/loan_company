from datetime import datetime, date
from sqlalchemy import BigInteger, String, Integer, DateTime, JSON, Date
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, LoanStatus
import phonenumbers  # pip install phonenumbers
from pydantic import EmailStr, BaseModel  # pip install pydantic[email]
from sqlalchemy import Column, ForeignKey, Numeric, Enum, String
from sqlalchemy.orm import relationship



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

    loans = relationship("Loan", back_populates="client", cascade="all, delete-orphan")

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



class Loan(Base):
    """Модель кредита клиента"""
    __tablename__ = 'loans'

    loan_id = Column(Integer, primary_key=True, autoincrement=True,
                   comment='Уникальный идентификатор кредита')
    client_id = Column(Integer, ForeignKey('clients.clientID', ondelete='CASCADE'),
                     nullable=False, index=True,
                     comment='Ссылка на клиента')
    loan_type_id = Column(Integer, ForeignKey('loan_types.type_id'),
                       nullable=False, index=True,
                       comment='Ссылка на тип кредита')
    issue_date = Column(DateTime, default=datetime.utcnow, nullable=False,
                      comment='Дата выдачи кредита')
    amount = Column(Numeric(15, 2), nullable=False,
                  comment='Сумма кредита')
    term = Column(Integer, nullable=False,
                comment='Срок кредита (в месяцах)')
    status = Column(Enum(LoanStatus), nullable=False, default=LoanStatus.ACTIVE,
                  comment='Статус кредита')
    total_paid = Column(Numeric(15, 2), default=0.00, nullable=False,
                      comment='Общая сумма выплаченных средств')
    remaining_amount = Column(Numeric(15, 2), nullable=False,
                       comment='Оставшаяся сумма к выплате')
    # Связи
    client = relationship("Client", back_populates="loans")
    loan_type = relationship("LoanType")
    payments = relationship("Payment", back_populates="loan", cascade="all, delete-orphan",
                          order_by="Payment.payment_date_plan")

    def __repr__(self):
        return (f"<Loan {self.loan_id} (Client: {self.client_id}, "
                f"Amount: {self.amount}, Status: {self.status.value})>")

    def update_status(self):
        """Автоматическое обновление статуса кредита"""
        if self.remaining_amount <= 0:
            self.status = LoanStatus.CLOSED


class Payment(Base):
    """Модель платежа по кредиту"""
    __tablename__ = 'payments'

    payment_id = Column(Integer, primary_key=True, autoincrement=True,
                      comment='Уникальный идентификатор платежа (PK)')

    loan_id = Column(Integer, ForeignKey('loans.loan_id', ondelete='CASCADE'),
                   nullable=False, index=True,
                   comment='Ссылка на кредит (FK)')

    payment_date_plan = Column(Date, nullable=False,
                             comment='Плановая дата внесения платежа')

    planned_amount = Column(Numeric(15, 2), nullable=False,
                          comment='Плановая сумма платежа')

    payment_date_fact = Column(Date,
                             comment='Фактическая дата внесения платежа (NULL если не оплачен)')

    actual_amount = Column(Numeric(15, 2), default=0.00,
                         comment='Фактически внесенная сумма')

    penalty_date = Column(Date,
                        comment='Дата начисления штрафа (NULL если нет штрафа)')

    penalty_amount = Column(Numeric(15, 2), default=0.00,
                          comment='Сумма штрафа за просрочку')

    # Связи
    loan = relationship("Loan", back_populates="payments")

    def __repr__(self):
        return f"<Payment {self.payment_id} (Loan: {self.loan_id}, Plan: {self.planned_amount})>"

    def calculate_penalty(self, current_date: date = date.today()):
        """Расчет штрафа за просрочку платежа"""
        if not self.payment_date_fact and self.payment_date_plan < current_date:
            days_overdue = (current_date - self.payment_date_plan).days
            self.penalty_amount = self.planned_amount * 0.01 * days_overdue  # 1% за каждый день
            self.penalty_date = current_date
            return self.penalty_amount
        return 0.00
