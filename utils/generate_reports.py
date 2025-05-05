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

        if loan.status != LoanStatus.CLOSED:
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
            .where(Payment.payment_date_plan < date(2025, 10, 4)) # Изменил с date.today() для проверки
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
    """Генерирует финансовый отчет за календарный год с разбивкой по месяцам и кварталам"""
    try:
        logging.debug(f"Начало генерации финансового отчета за {year} год")

        # Создаем структуры для хранения данных по месяцам и кварталам
        months_data = {month: {
            'loans': 0,
            'issued': Decimal('0'),
            'paid_loans': 0,
            'active_loans': 0,
            'payments': 0,
            'paid': Decimal('0'),
            'overdue_payments': 0,
            'overdue_amount': Decimal('0')
        } for month in range(1, 13)}

        quarters_data = {quarter: {
            'loans': 0,
            'issued': Decimal('0'),
            'paid_loans': 0,
            'active_loans': 0,
            'payments': 0,
            'paid': Decimal('0'),
            'overdue_payments': 0,
            'overdue_amount': Decimal('0')
        } for quarter in range(1, 5)}

        # Получаем все кредиты за год
        loans_query = select(Loan).where(func.extract('year', Loan.issue_date) == year)
        loans_result = await session.scalars(loans_query)
        loans = loans_result.all()
        logging.debug(f"Найдено кредитов: {len(loans)}")

        total_issued = Decimal('0')
        total_loans = len(loans)
        paid_loans = 0
        active_loans = 0

        for loan in loans:
            if loan.amount is not None:
                month = loan.issue_date.month
                quarter = (month - 1) // 3 + 1
                amount = Decimal(str(loan.amount))

                months_data[month]['loans'] += 1
                months_data[month]['issued'] += amount
                quarters_data[quarter]['loans'] += 1
                quarters_data[quarter]['issued'] += amount

                total_issued += amount

                if loan.status == LoanStatus.CLOSED:
                    months_data[month]['paid_loans'] += 1
                    quarters_data[quarter]['paid_loans'] += 1
                    paid_loans += 1
                elif loan.status == LoanStatus.ACTIVE:
                    months_data[month]['active_loans'] += 1
                    quarters_data[quarter]['active_loans'] += 1
                    active_loans += 1

        logging.debug(f"Кредиты: Всего={total_loans}, Погашенные={paid_loans}, Активные={active_loans}, Сумма={total_issued}")

        # Получаем все платежи за год
        payments_query = select(Payment).where(
            func.extract('year', Payment.payment_date_fact) == year
        ).where(Payment.actual_amount.is_not(None))
        payments_result = await session.scalars(payments_query)
        payments = payments_result.all()
        logging.debug(f"Найдено платежей: {len(payments)}")

        total_paid = Decimal('0')
        total_payments = len(payments)

        for payment in payments:
            if payment.actual_amount is not None and payment.payment_date_fact is not None:
                month = payment.payment_date_fact.month
                quarter = (month - 1) // 3 + 1
                amount = Decimal(str(payment.actual_amount))

                months_data[month]['payments'] += 1
                months_data[month]['paid'] += amount
                quarters_data[quarter]['payments'] += 1
                quarters_data[quarter]['paid'] += amount

                total_paid += amount

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

        total_overdue_amount = Decimal('0')

        for payment in overdue_payments:
            if payment.planned_amount is not None:
                month = payment.payment_date_plan.month
                quarter = (month - 1) // 3 + 1
                amount = Decimal(str(payment.planned_amount))

                months_data[month]['overdue_payments'] += 1
                months_data[month]['overdue_amount'] += amount
                quarters_data[quarter]['overdue_payments'] += 1
                quarters_data[quarter]['overdue_amount'] += amount

                total_overdue_amount += amount

        logging.debug(f"Просроченные платежи: Сумма={total_overdue_amount}")

        # Формируем отчет
        report = [
            f"<b>Финансовый отчет за {year} год</b>\n\n",
            f"📊 <b>Общие показатели:</b>\n",
            f"- Выдано кредитов: {total_loans}\n",
            f"- Общая сумма выданных кредитов: {total_issued:.2f} руб.\n",
            f"- Погашенные кредиты: {paid_loans}\n",
            f"- Активные кредиты: {active_loans}\n",
            f"- Всего платежей: {total_payments}\n",
            f"- Общая сумма платежей: {total_paid:.2f} руб.\n",
            f"- Просроченные платежи: {len(overdue_payments)}\n",
            f"- Сумма просроченных платежей: {total_overdue_amount:.2f} руб.\n\n",

            f"📅 <b>По кварталам:</b>\n"
        ]

        # Добавляем данные по кварталам
        for quarter in range(1, 5):
            q_data = quarters_data[quarter]
            report.append(
                f"<b>Квартал {quarter}:</b>\n"
                f"- Выдано кредитов: {q_data['loans']}\n"
                f"- Сумма кредитов: {q_data['issued']:.2f} руб.\n"
                f"- Погашенные кредиты: {q_data['paid_loans']}\n"
                f"- Активные кредиты: {q_data['active_loans']}\n"
                f"- Платежи: {q_data['payments']} ({q_data['paid']:.2f} руб.)\n"
                f"- Просрочки: {q_data['overdue_payments']} ({q_data['overdue_amount']:.2f} руб.)\n\n"
            )

        # Добавляем данные по месяцам
        report.append(f"📅 <b>По месяцам:</b>\n")
        month_names = [
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ]

        for month in range(1, 13):
            m_data = months_data[month]
            report.append(
                f"<b>{month_names[month-1]}:</b>\n"
                f"- Кредитов: {m_data['loans']} ({m_data['issued']:.2f} руб.)\n"
                f"- Платежи: {m_data['payments']} ({m_data['paid']:.2f} руб.)\n"
                f"- Просрочки: {m_data['overdue_payments']} ({m_data['overdue_amount']:.2f} руб.)\n\n"
            )

        report.append(f"📅 Дата формирования: {date.today().strftime('%d.%m.%Y')}")

        return "".join(report)
    except Exception as e:
        logging.error(f"Ошибка при генерации финансового отчета: {e}", exc_info=True)
        return "⚠ Произошла ошибка при формировании отчета"