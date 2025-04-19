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
    ------------------------------------------------------------------------------
    clientID            Уникальный внутренний ID клиента            INT, PK, AInc
    ------------------------------------------------------------------------------
    fullName            Полное имя (фамилия, имя, отчество)         STR(100)
    ------------------------------------------------------------------------------
    passport            Серия и номер паспорта (зашифровано)        STR(20), UQ
    ------------------------------------------------------------------------------
    telegram_id         ID Telegram для уведомлений                 BINT, UQ
    ------------------------------------------------------------------------------
    phone_numbers       Список телефонов в международном формате    JSON
    ------------------------------------------------------------------------------
    email               Контактный email (зашифровано)              STR(100), UQ0
    ------------------------------------------------------------------------------
    registration_date   Дата регистрации клиента                    DATE
    ------------------------------------------------------------------------------
    creditScore         Кредитный рейтинг (0-1000)                  INT
    ------------------------------------------------------------------------------

    ОТНОШЕНИЯ
    Loan            inf ---- 1    Clients
    CreditHistory   inf ---- inf    Clients
    """
    __tablename__ = "clients"
    __table_args__ = {
        'comment': 'Таблица клиентов кредитной организации'
    }

    # Основные поля
    clientID = Column(Integer,primary_key=True,autoincrement=True,
        comment="Уникальный внутренний ID клиента")
    fullName = Column(String(100),nullable=False,
        comment="Полное имя (фамилия, имя, отчество)")
    passport = Column(String(20),unique=True,nullable=False,
        comment="Серия и номер паспорта (зашифровано)" )
    telegram_id = Column(BigInteger,unique=True,nullable=True,
        comment="ID Telegram для уведомлений")
    phone_numbers = Column(JSON,nullable=False,
        comment="Список телефонов в международном формате"
    )
    email = Column(String(100),unique=True,nullable=True,
        comment="Контактный email (зашифровано)"
    )
    registration_date = Column(DateTime,default=datetime.utcnow,
        comment="Дата регистрации клиента"
    )
    creditScore = Column(Integer,default=0,
        comment="Кредитный рейтинг (0-1000)"
    )

    loans = relationship("Loan", back_populates="client", cascade="all, delete-orphan")
    # credit_history = relationship("CreditHistory", back_populates="client",
    #                             cascade="all, delete-orphan")
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
    """Модель кредита клиента
    Основные поля:
    ------------------------------------------------------------------------------
    loan_id             Уникальный идентификатор кредита    INT, PK, AInc
    ------------------------------------------------------------------------------
    client_id           Ссылка на клиента                   INT, FK
    ------------------------------------------------------------------------------
    loan_type_id        Ссылка на тип кредита               INT, FK
    ------------------------------------------------------------------------------
    issue_date          Дата выдачи кредита                 DATE
    ------------------------------------------------------------------------------
    amount              Сумма кредита                       NUM(15,2)
    ------------------------------------------------------------------------------
    term                Срок кредита (в месяцах)            INT
    ------------------------------------------------------------------------------
    status              Статус кредита                      ENUM
    ------------------------------------------------------------------------------
    total_paid          Общая сумма выплаченных средств     NUM(15,2)
    ------------------------------------------------------------------------------
    remaining_amount    Оставшаяся сумма к выплате          NUM(15,2)
    ------------------------------------------------------------------------------

    ОТНОШЕНИЯ
    clients     1 ---- inf    loans
    payments    inf ---- 1      loans
    loan_type   1   ---- inf    loans
    """
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
    """Модель платедей по кредиту
    Основные поля:
    ------------------------------------------------------------------------------
    payment_id          Уникальный идентификатор платежа    INT, PK, AInc
    ------------------------------------------------------------------------------
    loan_id             Ссылка на кредит                    INT, FK
    ------------------------------------------------------------------------------
    payment_date_plan   Плановая дата внесения платежа      DATE
    ------------------------------------------------------------------------------
    planned_amount      Плановая сумма платежа              NUM(15,2)
    ------------------------------------------------------------------------------
    payment_date_fact   Фактическая дата внесения платежа   DATE
    ------------------------------------------------------------------------------
    actual_amount       Фактически внесенная сумма          NUM(15,2)
    ------------------------------------------------------------------------------
    penalty_date        Дата начисления штрафа              DATE
    ------------------------------------------------------------------------------
    penalty_amount      Сумма штрафа за просрочку           NUM(15,2)
    ------------------------------------------------------------------------------

    ОТНОШЕНИЯ
    loans   1----inf    payments
    """
    __tablename__ = 'payments'

    payment_id = Column(Integer, primary_key=True, autoincrement=True,
                      comment='Уникальный идентификатор платежа (PK)')
    loan_id = Column(Integer, ForeignKey('loans.loan_id', ondelete='CASCADE'),nullable=False, index=True,
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


class CreditHistory(Base):
    """Модель кредитной истории
    Основные поля:
    ------------------------------------------------------------------------------
    LoanHistID      Уникальный внутренний ID клиента    INT, PK, AInc
    ------------------------------------------------------------------------------
    loanID          ID кредита                    INT, FK
    ------------------------------------------------------------------------------
    bankID          Название банка кредитования      DATE
    ------------------------------------------------------------------------------
    fullname        Полное имя клиента              NUM(15,2)
    ------------------------------------------------------------------------------
    passport        Паспортные данные клиента   DATE
    ------------------------------------------------------------------------------
    status          Статус кредита          NUM(15,2)
    ------------------------------------------------------------------------------
    issue_date      Дата выдачи кредита              DATE
    ------------------------------------------------------------------------------
    amount          Изначальная сумма кредита           NUM(15,2)
    ------------------------------------------------------------------------------
    term            Срок кредита в месяцах
    ------------------------------------------------------------------------------
    interest_rate   Процентная ставка (годовых)           NUM(15,2)
    ------------------------------------------------------------------------------

    ОТНОШЕНИЯ
    cliets   1----inf    credit_history
    """

    __tablename__ = "credit_history"

    LoanHistID      = Column(Integer,primary_key=True,autoincrement=True,
        comment="Уникальный внутренний ID клиента")
    loanID          = Column(Integer,
        comment="ID кредита (общие-организационный)")
    bankID          = Column(Integer, ForeignKey('bank_name.bankID'),
        comment='Название банка кредитования')
    fullname        = Column(String(100), nullable=False,
        comment="Полное имя клиента")
    passport        = Column(Integer, nullable=False,
        comment="Паспортные данные клиента")
    status          = Column(Enum(LoanStatus),nullable=False, default=LoanStatus.UNKNOW,
        comment="Статус кредита")
    issue_date      = Column(Date, nullable=False,
        comment='Дата выдачи кредита')
    amount          = Column(Numeric(15, 2), nullable=False,
        comment='Изначальная сумма кредита')
    term            = Column(Integer, nullable=False,
        comment='Срок кредита в месяцах')
    interest_rate   = Column(Numeric(5, 2), nullable=False,
        comment='Процентная ставка (годовых)')

    # Связь с клиентом (только для наших клиентов)
    # client = relationship("Client", back_populates="credit_history")

    def __repr__(self):
        return (f"<CreditHistory {self.history_id} (Bank: {self.bank_name}, "
                f"Amount: {self.amount}, Status: {self.status.value})>")

    def is_external(self) -> bool:
        """Проверяет, является ли кредит внешним (не из нашей системы)"""
        return self.loan_id is None or not hasattr(self, 'loan')