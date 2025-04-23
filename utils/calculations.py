from models.user import Client, Loan, Payment, CreditHistory
from models.base import LoanType, LoanStatus
from datetime import date,datetime, timedelta
from decimal import Decimal,getcontext
from sqlalchemy import select
from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession


async def calculate_max_loan_amount(client_id: int, session) -> Decimal:
    """Рассчитывает максимально доступную сумму кредита"""
    client = await session.get(Client, client_id)
    
    if client.creditScore >= 800:
        return Decimal('1000000')
    elif client.creditScore >= 600:
        return Decimal('500000')
    elif client.creditScore >= 400:
        return Decimal('200000')
    else:
        return Decimal('50000')

def calculate_monthly_payment(amount: Decimal, term: int, interest_rate: float) -> Decimal:
    """Рассчитывает ежемесячный платеж"""
    getcontext().prec = 10
    monthly_rate = interest_rate / 100 / 12
    annuity_coeff = ((monthly_rate * (1 + monthly_rate)**term)/((1 + monthly_rate)**term - 1))
    return amount * Decimal(annuity_coeff)

async def generate_payment_schedule(
    loan_id: int,
    amount: Decimal,
    term: int,
    interest_rate: float,
    start_date: date = date.today(),
    session: AsyncSession = None
) -> list[Payment]:
    """
    Генерирует график платежей по аннуитетному кредиту и сохраняет в БД
    
    :param loan_id: ID кредита
    :param amount: Сумма кредита
    :param term: Срок в месяцах
    :param interest_rate: Годовая процентная ставка
    :param start_date: Дата первого платежа
    :param session: AsyncSession для работы с БД
    :return: список объектов Payment
    """
    getcontext().prec = 10
    monthly_rate = Decimal(interest_rate) / Decimal(100) / Decimal(12)
    monthly_payment = calculate_monthly_payment(amount, term, interest_rate)
    
    remaining_balance = amount
    payment_date = start_date
    
    payments = []  # Инициализация списка для хранения платежей
    
    for month in range(1, term + 1):
        payment_date = payment_date + relativedelta(months=1)
        interest_payment = remaining_balance * monthly_rate
        principal_payment = monthly_payment - interest_payment
        remaining_balance -= principal_payment
        
        # Корректировка последнего платежа
        if month == term:
            principal_payment += remaining_balance
            remaining_balance = Decimal(0)
        
        # Создаем платеж
        payment = Payment(
            loan_id=loan_id,
            payment_date_plan=payment_date,
            planned_amount=float(monthly_payment),
            payment_date_fact=None,
            actual_amount=None,
            penalty_date=None,
            penalty_amount=None
        )
        
        # Добавляем в сессию и список
        session.add(payment)
        payments.append(payment)
    
    await session.commit()

    return payments  # Возвращаем список платежей
