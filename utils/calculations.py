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
    start_date: date = None,
    session: AsyncSession = None
) -> list[Payment]:
    """
    Генерация графика платежей по аннуитетному кредиту с корректной начальной датой.

    :param loan_id: ID кредита
    :param amount: Сумма кредита
    :param term: Срок в месяцах
    :param interest_rate: Годовая процентная ставка
    :param start_date: (опционально) дата начала нового графика
    :param session: сессия БД
    :return: список новых платежей
    """
    getcontext().prec = 10
    monthly_rate = Decimal(interest_rate) / Decimal(100) / Decimal(12)
    monthly_payment = calculate_monthly_payment(amount, term, interest_rate)

    # Определим start_date: от последнего платежа или сегодняшнего дня
    if not start_date:
        # Ищем последний плановый платеж
        last_payment = await session.scalar(
            select(Payment)
            .where(Payment.loan_id == loan_id)
            .order_by(Payment.payment_date_plan.desc())
            .limit(1)
        )
        if last_payment:
            start_date = last_payment.payment_date_plan
        else:
            # Фолбэк — сегодня
            start_date = date.today()

    # Начнём с даты следующего месяца после start_date
    payment_date = start_date + relativedelta(months=1)
    remaining_balance = amount
    payments = []

    for month in range(1, term + 1):
        interest_payment = remaining_balance * monthly_rate
        principal_payment = monthly_payment - interest_payment
        remaining_balance -= principal_payment

        # Корректировка последнего платежа
        if month == term:
            principal_payment += remaining_balance
            remaining_balance = Decimal(0)

        payment = Payment(
            loan_id=loan_id,
            payment_date_plan=payment_date,
            planned_amount=float(monthly_payment),
            payment_date_fact=None,
            actual_amount=None,
            penalty_date=None,
            penalty_amount=None
        )

        payments.append(payment)
        session.add(payment)

        # Следующая дата
        payment_date += relativedelta(months=1)

    await session.commit()
    return payments

async def calculate_next_payment_details(loan: Loan, session: AsyncSession) -> tuple[date, Decimal]:
    """Рассчитывает дату и сумму следующего платежа"""
    # Получаем тип кредита, чтобы взять процентную ставку
    loan_type = await session.get(LoanType, loan.loan_type_id)
    if not loan_type:
        raise ValueError("Тип кредита не найден")

    # Получаем последний запланированный платеж (где payment_date_plan не None)
    last_scheduled_payment = await session.scalar(
        select(Payment)
        .where(Payment.loan_id == loan.loan_id)
        .where(Payment.payment_date_plan.is_not(None))
        .order_by(Payment.payment_date_plan.desc())
    )
    
    if last_scheduled_payment:
        # Ищем следующий платеж в графике
        next_payment = await session.scalar(
            select(Payment)
            .where(Payment.loan_id == loan.loan_id)
            .where(Payment.payment_date_plan > last_scheduled_payment.payment_date_plan)
            .order_by(Payment.payment_date_plan.asc())
        )
        
        if next_payment:
            return next_payment.payment_date_plan, Decimal(str(next_payment.planned_amount))
    
    # Если нет данных о платежах, рассчитываем по умолчанию
    if loan.issue_date and loan.term:
        monthly_payment = calculate_monthly_payment(
            Decimal(str(loan.amount)), 
            loan.term, 
            float(loan_type.interest_rate)  # Используем ставку из LoanType
        )
        
        # Определяем следующую дату платежа
        months_passed = 1
        if last_scheduled_payment:
            months_passed = (last_scheduled_payment.payment_date_plan.year - loan.issue_date.year) * 12 + \
                           (last_scheduled_payment.payment_date_plan.month - loan.issue_date.month) + 1
        
        next_date = loan.issue_date + relativedelta(months=months_passed)
        return next_date, monthly_payment
    
    # Если нет данных для расчета, используем текущую дату и остаток
    return date.today(), Decimal(str(loan.remaining_amount))

async def calculate_next_payment_date_after_payment(loan: Loan, session: AsyncSession) -> date:
    """Рассчитывает дату следующего платежа после текущего платежа"""
    # Находим следующий незавершенный платеж по графику
    next_payment = await session.scalar(
        select(Payment)
        .where(Payment.loan_id == loan.loan_id)
        .where(Payment.actual_amount.is_(None))  # Только незавершенные платежи
        .order_by(Payment.payment_date_plan.asc())
        .limit(1)
    )
    
    if next_payment:
        return next_payment.payment_date_plan
    
    # Если все платежи завершены, возвращаем None
    return None

async def generate_shortened_schedule(
    loan: Loan,
    monthly_payment: Decimal,
    start_date: date,
    session: AsyncSession
) -> list[Payment]:
    """
    Генерация нового графика платежей после досрочного погашения
    с сохранением размера платежа и сокращением срока кредита.
    
    :param loan: Объект кредита
    :param monthly_payment: Размер ежемесячного платежа
    :param start_date: Дата начала новых платежей
    :param session: Сессия БД
    :return: Список новых платежей
    """
    getcontext().prec = 10
    monthly_rate = Decimal(loan.loan_type.interest_rate) / Decimal(100) / Decimal(12)
    
    payments = []
    remaining_balance = loan.remaining_amount
    payment_date = start_date + relativedelta(months=1)

    while remaining_balance > 0:
        interest_payment = remaining_balance * monthly_rate
        principal_payment = monthly_payment - interest_payment

        if principal_payment <= 0:
            raise ValueError("Размер ежемесячного платежа слишком мал для погашения кредита.")

        if principal_payment >= remaining_balance:
            principal_payment = remaining_balance
            monthly_total_payment = principal_payment + interest_payment
        else:
            monthly_total_payment = monthly_payment

        payment = Payment(
            loan_id=loan.loan_id,
            payment_date_plan=payment_date,
            planned_amount=float(monthly_total_payment),
            payment_date_fact=None,
            actual_amount=None
        )
        payments.append(payment)

        remaining_balance -= principal_payment
        payment_date += relativedelta(months=1)

    session.add_all(payments)
    await session.flush()  # Только фиксируем в сессии, коммит позже с другими изменениями

    return payments
