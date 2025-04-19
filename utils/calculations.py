from models.user import Client, Loan, Payment, CreditHistory
from models.base import LoanType, LoanStatus
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select

async def calculate_max_loan_amount(client_id: int, session) -> Decimal:
    """Рассчитывает максимально доступную сумму кредита"""
    # TO DO добавить логику рассчета макс суммы
    credit_history = await session.execute(
        select(CreditHistory)
        .where(CreditHistory.LoanHistID == client_id)
    )
    history = credit_history.scalars().all()
    

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
    """Рассчитывает примерный ежемесячный платеж"""
    # TO DO добавить логику рассчета
    monthly_rate = interest_rate / 100 / 12
    annuity_coeff = (monthly_rate * (1 + monthly_rate)**term) / ((1 + monthly_rate)**term - 1)
    return amount * Decimal(annuity_coeff)


def generate_payment_schedule(amount: Decimal, term: int, interest_rate: float) -> list[Payment]:
    """
    Генерирует график платежей по кредиту
    :param amount: Сумма кредита
    :param term: Срок в месяцах (целое число)
    :param interest_rate: Годовая процентная ставка, например 12.5
    :return: Список платежей (Payment)
    """
    # TO DO добавить логику рассчета 
    monthly_payment = calculate_monthly_payment(amount, term, interest_rate)
    payments = []
    today = datetime.now().date()
    remaining = amount

    for month in range(1, term + 1):
        payment_date = today + timedelta(days=30 * month)
        interest = remaining * Decimal(interest_rate) / Decimal(100 * 12)
        principal = monthly_payment - interest

        payments.append(Payment(
            payment_date_plan=payment_date,
            planned_amount=round(monthly_payment, 2),
        ))

        remaining -= principal

    if remaining != Decimal("0.00"):
        payments[-1].planned_amount += round(remaining, 2)

    return payments