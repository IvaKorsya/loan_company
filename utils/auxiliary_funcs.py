from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from datetime import date
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import Loan, Payment, Client
from models.base import LoanStatus
from typing import Optional
from aiogram import types


def get_max_credit_amount(score: int) -> Decimal:
    """Вычисление максимально возможной суммы кредита"""
    if score >= 800:
        return Decimal(1000000)  # Примерная сумма для отличного рейтинга
    elif score >= 600:
        return Decimal(500000)  # Примерная сумма для хорошего рейтинга
    elif score >= 400:
        return Decimal(50000)  # Примерная сумма для удовлетворительного рейтинга
    else:
        return Decimal(0)  # Низкий рейтинг, кредит не доступен


def get_credit_status(score: int) -> str:
    """Возвращает текстовый статус в зависимости от рейтинга"""
    if score >= 800:
        return "Отличный - высокий приоритет одобрения"
    elif score >= 600:
        return "Хороший - стандартные условия"
    elif score >= 400:
        return "Удовлетворительный - повышенные ставки"
    else:
        return "Низкий - требуется дополнительная проверка"

def get_credit_advice(score: int) -> str:
    """Генерирует рекомендации для улучшения рейтинга"""
    advice = []
    if score < 700:
        advice.append("- Своевременно погашайте кредиты")
    if score < 500:
        advice.append("- Увеличьте частоту использования сервиса")
    if score < 300:
        advice.append("- Обратитесь в отделение для консультации")

    return "\n".join(advice) if advice else "Ваш рейтинг оптимальный!"

async def get_client_by_telegram(session, telegram_id: int) -> Optional[Client]:
    """Получает клиента по telegram_id"""
    return await session.scalar(
        select(Client)
        .where(Client.telegram_id == telegram_id)
    )

async def check_client_registered(message: types.Message, session) -> Optional[Client]:
    """Проверяет регистрацию клиента и возвращает его, если он зарегистрирован"""
    client = await get_client_by_telegram(session, message.from_user.id)
    if not client:
        await message.answer("ℹ Вы не зарегистрированы. Используйте /register")
        return None
    return client

async def update_payment_and_loan(session, payment, loan, amount, payment_date, loan_id):
    """Обновляет платеж и данные кредита"""
    try:
        # Обновляем данные платежа
        payment.payment_date_fact = payment_date
        payment.actual_amount = float(amount)
        
        # Обновляем остаток по кредиту
        loan.remaining_amount -= Decimal(str(amount))
        
        # Находим следующий платеж
        next_payment = await session.scalar(
            select(Payment)
            .where(Payment.loan_id == loan_id)
            .where(Payment.payment_date_fact.is_(None))
            .order_by(Payment.payment_date_plan.asc())
            .limit(1)
        )
        
        # Обновляем дату следующего платежа
        loan.next_payment_date = next_payment.payment_date_plan if next_payment else None
        
        # Если кредит полностью погашен
        if loan.remaining_amount <= 0:
            loan.status = "PAID"
            loan.next_payment_date = None
        
        await session.commit()
        
    except Exception as e:
        logging.error(f"Ошибка при обновлении платежа и кредита: {e}", exc_info=True)
        raise

async def show_payment_schedule(message: Message, loan_id: int, session: AsyncSession):
    """Выводит график платежей по кредиту"""
    try:
        # Получаем данные по кредиту
        loan = await session.get(Loan, loan_id)
        if not loan:
            await message.answer("❌ Кредит не найден")
            return False

        # Получаем все платежи по кредиту
        payments = await session.scalars(
            select(Payment)
            .where(Payment.loan_id == loan_id)
            .order_by(Payment.payment_date_plan.asc())
        )
        payments = payments.all()

        if not payments:
            await message.answer("ℹ По этому кредиту нет запланированных платежей")
            return False

        # Формируем заголовок сообщения
        status = "✅ Закрыт" if loan.status == LoanStatus.CLOSED else "🟡 Активен"
        msg = [
            f"<b>График платежей по кредиту #{loan_id}</b>",
            f"🔹 Статус: {status}",
            f"🔹 Сумма кредита: {loan.amount:.2f} руб.",
            f"🔹 Остаток долга без процентов: {loan.remaining_amount:.2f} руб.",
            f"🔹 Срок: {loan.term} мес.",
            "\n<b>Дата\t\tСумма\t\tСтатус</b>"
        ]

        # Добавляем информацию о каждом платеже
        for payment in payments:
            payment_date = payment.payment_date_plan.strftime('%d.%m.%Y')
            amount = f"{Decimal(str(payment.planned_amount)):.2f} руб."
            
            if payment.payment_date_fact:
                status = "✅ Оплачен"
                if payment.payment_date_fact > payment.payment_date_plan:
                    days_late = (payment.payment_date_fact - payment.payment_date_plan).days
                    status = f"⚠ Оплачен с опозданием ({days_late} дн.)"
            else:
                if payment.payment_date_plan < date.today():
                    days_late = (date.today() - payment.payment_date_plan).days
                    status = f"❌ Просрочен ({days_late} дн.)"
                else:
                    status = "🟡 Ожидает оплаты"

            msg.append(f"{payment_date}\t{amount}\t{status}")

        # Добавляем итоговую информацию
        total_paid = sum(
            Decimal(str(p.actual_amount)) 
            for p in payments 
            if p.actual_amount is not None
        )
        total_planned = sum(Decimal(str(p.planned_amount)) for p in payments)
        
        msg.extend([
            "\n<b>Итого:</b>",
            f"🔹 Запланировано: {total_planned:.2f} руб.",
            f"🔹 Оплачено: {total_paid:.2f} руб.",
            f"🔹 Осталось: {total_planned - total_paid:.2f} руб."
        ])

        # Отправляем сообщение
        await message.answer(
            "\n".join(msg),
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
        return True

    except Exception as e:
        logging.error(f"Ошибка при выводе графика платежей: {e}", exc_info=True)
        await message.answer(
            "⚠ Произошла ошибка при получении графика платежей",
            reply_markup=ReplyKeyboardRemove()
        )
        return False