from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, Numeric
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.types import TypeDecorator
from enum import Enum as PyEnum

class LoanStatusType(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return value.value if value else None

    def process_result_value(self, value, dialect):
        return LoanStatus(value) if value else None

class LoanStatus(PyEnum):
    """
    Enum класс для статуса кредита
        ACTIVE  'активен'
        CLOSED  'закрыт'
        OVERDUE 'просрочен'
        UNKNOW  'неизвестно'
    """
    ACTIVE = 'активен'
    CLOSED = 'закрыт'
    OVERDUE = 'просрочен'
    UNKNOW = 'неизвестно'

class Base(AsyncAttrs, DeclarativeBase):
    """Базовая модель с поддержкой async"""
    pass

class LoanType(Base):
    """
    Модель типа кредита
    Таблица : loan_types
        type_id         ID типа кредита             [INT, PK]
        name            названия кредитования       [STR[100]]
        interest_rate   годовая процентная ставка   [INT]
        min_amount      минимальная сумма кредита   [INT]
        max_amount      макисмальная сумма кредита  [INT]
        min_term        минимальный срок кредитования  INT]
        max_term        макисмальный срок кредитования [INT]
        description     описание кредита            [STR[500]]
    """
    __tablename__ = 'loan_types'

    type_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    interest_rate = Column(Numeric(5, 2), nullable=False)
    min_amount = Column(Numeric(15, 2), nullable=False)
    max_amount = Column(Numeric(15, 2), nullable=False)
    min_term = Column(Numeric(15), nullable=False)
    max_term = Column(Numeric(15), nullable=False)
    description = Column(String(500))

    def __repr__(self):
        return f"<LoanType {self.type_id}: {self.name}>"

class BankName(Base):
    """
    Модель банка кредитования
    Таблица : bank_name
        bankID  ID банка кредитования   [INT, PK]
        name    названия банка          [STR[100]]
    """
    __tablename__ = 'bank_name'

    bankID = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)