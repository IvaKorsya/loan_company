import logging
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import Client, Loan, Payment
from models.base import LoanStatus
from typing import Optional

async def generate_no_obligations_doc(loan_id: int, session: AsyncSession) -> Optional[str]:
    """Генерирует документ об отсутствии взаимных обязательств"""
    try:
        loan = await session.get(Loan, loan_id)
        if not loan:
            return None

        client = await session.get(Client, loan.client_id)
        if not client:
            return None

        if loan.status != LoanStatus.PAID:
            return None

        total_paid = await session.scalar(
            select(func.sum(Payment.actual_amount))
            .where(Payment.loan_id == loan_id)
            .where(Payment.actual_amount.is_not(None))
        )

        return (
            f"<b>Справка об отсутствии взаимных обязательств</b>\n\n"
            f"Дата: {date.today().strftime('%d.%m.%Y')}\n"
            f"Клиент: {client.fullName}\n"
            f"ID клиента: {client.clientID}\n"
            f"ID кредита: {loan_id}\n"
            f"Сумма кредита: {loan.amount:.2f} руб.\n"
            f"Оплачено: {total_paid:.2f} руб.\n"
            f"Статус: Полностью погашен\n\n"
            f"Настоящим подтверждается, что по состоянию на {date.today().strftime('%d.%m.%Y')} "
            f"у клиента {client.fullName} отсутствуют обязательства перед кредитной организацией "
            f"по кредитному договору #{loan_id}."
        )
    except Exception as e:
        logging.error(f"Ошибка при генерации документа об отсутствии обязательств: {e}", exc_info=True)
        return None

async def generate_court_notice(loan_id: int, session: AsyncSession) -> Optional[str]:
    """Генерирует повестку в суд при ≥3 просроченных платежах"""
    try:
        loan = await session.get(Loan, loan_id)
        if not loan:
            return None

        client = await session.get(Client, loan.client_id)
        if not client:
            return None

        payments = await session.scalars(
            select(Payment)
            .where(Payment.loan_id == loan_id)
            .where(Payment.payment_date_fact.is_(None))
            .where(Payment.payment_date_plan < date.today())
        )
        overdue_payments = payments.all()

        if len(overdue_payments) < 3:
            return None

        total_overdue = sum(Decimal(str(p.planned_amount)) for p in overdue_payments)
        overdue_details = "\n".join(
            f"- {p.payment_date_plan.strftime('%d.%m.%Y')}: {Decimal(str(p.planned_amount)):.2f} руб."
            for p in overdue_payments
        )

        return (
            f"<b>Уведомление о намерении обратиться в суд</b>\n\n"
            f"Дата: {date.today().strftime('%d.%m.%Y')}\n"
            f"Клиент: {client.fullName}\n"
            f"ID клиента: {client.clientID}\n"
            f"ID кредита: {loan_id}\n"
            f"Сумма кредита: {loan.amount:.2f} руб.\n"
            f"Остаток долга: {loan.remaining_amount:.2f} руб.\n\n"
            f"<b>Просроченные платежи:</b>\n{overdue_details}\n"
            f"Общая сумма просрочки: {total_overdue:.2f} руб.\n\n"
            f"Уважаемый {client.fullName},\n"
            f"В связи с наличием {len(overdue_payments)} просроченных платежей по кредитному договору #{loan_id}, "
            f"кредитная организация уведомляет о намерении обратиться в суд для взыскания задолженности. "
            f"Просим в кратчайшие сроки погасить задолженность во избежание судебного разбирательства."
        )
    except Exception as e:
        logging.error(f"Ошибка при генерации повестки в суд: {e}", exc_info=True)
        return None

async def generate_annual_financial_report(year: int, session: AsyncSession) -> str:
    """Генерирует финансовый отчет за календарный год"""
    try:
        logging.debug(f"Начало генерации финансового отчета за {year} год")

        # Получаем все кредиты за год
        loans_query = select(Loan).where(func.extract('year', Loan.issue_date) == year)
        loans_result = await session.scalars(loans_query)
        loans = loans_result.all()
        logging.debug(f"Найдено кредитов: {len(loans)}")

        total_issued = sum(Decimal(str(loan.amount)) for loan in loans if loan.amount is not None)
        total_loans = len(loans)
        paid_loans = len([loan for loan in loans if loan.status == LoanStatus.PAID])
        active_loans = len([loan for loan in loans if loan.status == LoanStatus.ACTIVE])
        logging.debug(f"Кредиты: Всего={total_loans}, Погашенные={paid_loans}, Активные={active_loans}, Сумма={total_issued}")

        # Получаем все платежи за год
        payments_query = select(Payment).where(
            func.extract('year', Payment.payment_date_fact) == year
        ).where(Payment.actual_amount.is_not(None))
        payments_result = await session.scalars(payments_query)
        payments = payments_result.all()
        logging.debug(f"Найдено платежей: {len(payments)}")

        total_paid = sum(Decimal(str(p.actual_amount)) for p in payments if p.actual_amount is not None)
        total_payments = len(payments)
        logging.debug(f"Платежи: Всего={total_payments}, Сумма={total_paid}")

        # Получаем просроченные платежи
        overdue_payments_query = select(Payment).where(
            Payment.payment_date_fact.is_(None)
        ).where(Payment.payment_date_plan < date.today()).where(
            func.extract('year', Payment.payment_date_plan) == year
        )
        overdue_payments_result = await session.scalars(overdue_payments_query)
        overdue_payments = overdue_payments_result.all()
        logging.debug(f"Найдено просроченных платежей: {len(overdue_payments)}")

        total_overdue_amount = sum(Decimal(str(p.planned_amount)) for p in overdue_payments if p.planned_amount is not None)
        logging.debug(f"Просроченные платежи: Сумма={total_overdue_amount}")

        return (
            f"<b>Финансовый отчет за {year} год</b>\n\n"
            f"📊 <b>Кредитная деятельность:</b>\n"
            f"- Выдано кредитов: {total_loans}\n"
            f"- Общая сумма выданных кредитов: {total_issued:.2f} руб.\n"
            f"- Погашенные кредиты: {paid_loans}\n"
            f"- Активные кредиты: {active_loans}\n\n"
            f"💸 <b>Платежи:</b>\n"
            f"- Всего платежей: {total_payments}\n"
            f"- Общая сумма платежей: {total_paid:.2f} руб.\n"
            f"- Просроченные платежи: {len(overdue_payments)}\n"
            f"- Сумма просроченных платежей: {total_overdue_amount:.2f} руб.\n\n"
            f"📅 Дата формирования: {date.today().strftime('%d.%m.%Y')}"
        )
    except Exception as e:
        logging.error(f"Ошибка при генерации финансового отчета: {e}", exc_info=True)
        return "⚠ Произошла ошибка при формировании отчета"