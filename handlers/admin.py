from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext  # Добавлен импорт для FSMContext
from sqlalchemy import select, update, func, and_
from sqlalchemy.orm import joinedload
from utils.commands import set_bot_commands
from utils.database import async_session
from models import Client, Loan, Payment, LoanType, LoanStatus
from config import Config
from datetime import datetime, date
from decimal import Decimal
from utils.calculations import calculate_monthly_payment, calculate_max_loan_amount
from utils.generate_files import generate_payments_csv
import logging

router = Router(name="admin_handlers")

# Проверка админских прав
async def is_admin(user_id: int) -> bool:
    """
    Проверка на право администрирования.
    """
    return user_id in Config.ADMINS

# Постоянная навигационная клавиатура
def get_admin_nav_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        types.InlineKeyboardButton(text="👥 Поиск клиента", callback_data="admin_find_client")
    )
    builder.row(
        types.InlineKeyboardButton(text="⚙ Изменить рейтинг", callback_data="admin_change_credit"),
        types.InlineKeyboardButton(text="💳 Выдать кредит", callback_data="admin_issue_loan")
    )
    builder.row(
        types.InlineKeyboardButton(text="💸 Принять платеж", callback_data="admin_make_payment"),
        types.InlineKeyboardButton(text="🔄 Досрочное погашение", callback_data="admin_early_repayment")
    )
    builder.row(
        types.InlineKeyboardButton(text="📈 Отчёты", callback_data="admin_reports")
    )
    return builder.as_markup()

# ---- Админские команды ----

@router.message(Command("admin"))
async def admin_auth(message: types.Message):
    """
    Аутентификация администратора.
    Запрашивает пароль, если пользователь в списке админов.
    """
    if not await is_admin(message.from_user.id):
        return await message.answer("❌ Доступ запрещен")

    await message.answer(
        "🔐 <b>Панель администратора</b>\n"
        "Введите пароль для доступа:",
        parse_mode=ParseMode.HTML,
        reply_markup=types.ReplyKeyboardRemove()
    )

@router.message(F.text == Config.ADMIN_PASSWORD)
async def admin_panel(message: types.Message, bot: Bot):
    """
    Основное меню админки с навигационной клавиатурой.
    """
    if not await is_admin(message.from_user.id):
        return

    await set_bot_commands(bot, message.from_user.id)

    await message.answer(
        "🛠 <b>Административная панель</b>\n"
        "Выберите действие:",
        reply_markup=get_admin_nav_keyboard(),
        parse_mode=ParseMode.HTML
    )

# ---- Обработчики инлайн-кнопок ----

@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: types.CallbackQuery):
    """
    Показывает статистику системы.
    """
    async with async_session() as session:
        clients_count = await session.scalar(select(func.count(Client.clientID)))
        avg_score = await session.scalar(select(func.avg(Client.creditScore)))
        total_loans = await session.scalar(select(func.count(Loan.loan_id)))
        active_loans = await session.scalar(
            select(func.count(Loan.loan_id))
            .where(Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE]))
        )

    await callback.message.edit_text(
        f"📈 <b>Статистика системы</b>\n\n"
        f"• Всего клиентов: <b>{clients_count}</b>\n"
        f"• Средний кредитный рейтинг: <b>{avg_score:.1f}</b>\n"
        f"• Всего кредитов: <b>{total_loans}</b>\n"
        f"• Активных/просроченных кредитов: <b>{active_loans}</b>\n"
        f"• Администраторов: <b>{len(Config.ADMINS)}</b>",
        reply_markup=get_admin_nav_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data == "admin_find_client")
async def find_client(callback: types.CallbackQuery):
    """
    Поиск клиента по ID.
    """
    await callback.message.edit_text(
        "🔍 Введите ID клиента:",
        reply_markup=get_admin_nav_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.message.answer(
        "Введите ID клиента:",
        reply_markup=types.ForceReply(selective=True)
    )
    await callback.answer()

@router.message(F.reply_to_message & F.reply_to_message.text == "Введите ID клиента:")
async def process_client_id(message: types.Message):
    """
    Обработка ID клиента и вывод информации.
    """
    if not message.text.isdigit():
        return await message.answer("❌ ID должен быть числом")

    async with async_session() as session:
        client = await session.get(Client, int(message.text))

    if not client:
        return await message.answer("❌ Клиент не найден")

    await message.answer(
        f"👤 <b>Данные клиента</b>\n\n"
        f"• ID: <b>{client.clientID}</b>\n"
        f"• ФИО: <b>{client.fullName}</b>\n"
        f"• Телефон: <b>{client.phone_numbers[0] if client.phone_numbers else 'Нет'}</b>\n"
        f"• Email: <b>{client.email if client.email else 'Нет'}</b>\n"
        f"• Кредитный рейтинг: <b>{client.creditScore}</b>",
        reply_markup=get_admin_nav_keyboard(),
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data == "admin_change_credit")
async def change_credit_start(callback: types.CallbackQuery):
    """
    Изменение кредитного рейтинга.
    """
    await callback.message.edit_text(
        "✏ Введите ID клиента и новый рейтинг через пробел:\n"
        "<i>Пример: 42 750</i>",
        reply_markup=get_admin_nav_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.message.answer(
        "Введите ID клиента и новый рейтинг:",
        reply_markup=types.ForceReply(selective=True)
    )
    await callback.answer()

@router.message(F.reply_to_message & F.reply_to_message.text.startswith("Введите ID клиента и новый рейтинг:"))
async def process_credit_change(message: types.Message):
    """
    Обработка изменения кредитного рейтинга.
    """
    try:
        client_id, new_score = message.text.split()
        new_score = int(new_score)

        if not 0 <= new_score <= 1000:
            raise ValueError("Рейтинг должен быть от 0 до 1000")
    except:
        return await message.answer("❌ Неверный формат. Пример: <code>42 750</code>", parse_mode=ParseMode.HTML)

    async with async_session() as session:
        client = await session.get(Client, int(client_id))
        if not client:
            return await message.answer("❌ Клиент не найден")

        await session.execute(
            update(Client)
            .where(Client.clientID == int(client_id))
            .values(creditScore=new_score)
        )
        await session.commit()

    await message.answer(
        f"✅ Кредитный рейтинг клиента {client_id} изменен на {new_score}",
        reply_markup=get_admin_nav_keyboard()
    )

@router.callback_query(F.data == "admin_issue_loan")
async def issue_loan_start(callback: types.CallbackQuery):
    """
    Начало процесса выдачи кредита.
    """
    await callback.message.edit_text(
        "💳 Введите ID клиента для проверки возможности выдачи кредита:",
        reply_markup=get_admin_nav_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.message.answer(
        "Введите ID клиента:",
        reply_markup=types.ForceReply(selective=True)
    )
    await callback.answer()

@router.message(F.reply_to_message & F.reply_to_message.text == "Введите ID клиента:")
async def check_loan_eligibility(message: types.Message, state: FSMContext):
    """
    Проверка возможности выдачи кредита и выбор типа кредита.
    """
    if not message.text.isdigit():
        return await message.answer("❌ ID должен быть числом")

    client_id = int(message.text)
    async with async_session() as session:
        client = await session.get(Client, client_id)
        if not client:
            return await message.answer("❌ Клиент не найден")

        # Проверка активных или просроченных кредитов
        active_loans = await session.scalar(
            select(func.count(Loan.loan_id))
            .where(
                and_(
                    Loan.client_id == client_id,
                    Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE])
                )
            )
        )
        if active_loans > 0:
            return await message.answer(
                "❌ У клиента есть непогашенные кредиты. Новый кредит не может быть оформлен.",
                reply_markup=get_admin_nav_keyboard()
            )

        # Рассчитываем максимальную сумму кредита
        max_amount = await calculate_max_loan_amount(client_id, session)
        credit_score = client.creditScore

        # Определяем модификатор суммы в зависимости от кредитной истории
        overdue_loans = await session.scalar(
            select(func.count(Payment.payment_id))
            .where(
                Payment.loan_id.in_(
                    select(Loan.loan_id).where(Loan.client_id == client_id)
                )
            )
            .where(Payment.payment_date_fact.is_(None))
            .where(Payment.payment_date_plan < date.today())
        )
        if overdue_loans > 0:
            max_amount *= Decimal('0.7')  # 70% для клиентов с просрочками
        elif credit_score > 700:
            max_amount *= Decimal('1.2')  # 120% для хорошей кредитной истории
        else:
            max_amount *= Decimal('1.0')  # 100% для чистой кредитной истории

        # Получаем доступные типы кредитов
        loan_types = await session.execute(select(LoanType))
        loan_types = loan_types.scalars().all()

        if not loan_types:
            return await message.answer(
                "⚠ В настоящее время кредитные продукты недоступны",
                reply_markup=get_admin_nav_keyboard()
            )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"{lt.name} ({lt.interest_rate}%)",
                        callback_data=f"adminLoanType_{lt.type_id}_{client_id}"
                    )
                ] for lt in loan_types
            ]
        )

        await message.answer(
            f"👤 Клиент: {client.fullName}\n"
            f"📊 Кредитный рейтинг: {client.creditScore}\n"
            f"💰 Максимальная сумма: {max_amount:.2f} руб.\n\n"
            "Выберите тип кредита:",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )

@router.callback_query(F.data.startswith("adminLoanType_"))
async def process_loan_type(callback: types.CallbackQuery, state: FSMContext):
    """
    Обработка выбора типа кредита и запрос суммы.
    """
    try:
        _, type_id, client_id = callback.data.split("_")
        type_id, client_id = int(type_id), int(client_id)

        async with async_session() as session:
            loan_type = await session.get(LoanType, type_id)
            if not loan_type:
                return await callback.message.edit_text(
                    "❌ Тип кредита не найден",
                    reply_markup=get_admin_nav_keyboard()
                )

            client = await session.get(Client, client_id)
            if not client:
                return await callback.message.edit_text(
                    "❌ Клиент не найден",
                    reply_markup=get_admin_nav_keyboard()
                )

            max_amount = await calculate_max_loan_amount(client_id, session)
            overdue_loans = await session.scalar(
                select(func.count(Payment.payment_id))
                .where(
                    Payment.loan_id.in_(
                        select(Loan.loan_id).where(Loan.client_id == client_id)
                    )
                )
                .where(Payment.payment_date_fact.is_(None))
                .where(Payment.payment_date_plan < date.today())
            )
            if overdue_loans > 0:
                max_amount *= Decimal('0.7')
            elif client.creditScore > 700:
                max_amount *= Decimal('1.2')

            await state.update_data(
                client_id=client_id,
                loan_type_id=type_id,
                max_amount=float(max_amount),
                min_amount=loan_type.min_amount,
                max_term=loan_type.max_term,
                min_term=loan_type.min_term,
                interest_rate=loan_type.interest_rate
            )

        await callback.message.edit_text(
            f"💳 Тип кредита: {loan_type.name}\n"
            f"💰 Доступная сумма: от {loan_type.min_amount} до {max_amount:.2f} руб.\n"
            f"⏳ Срок: от {loan_type.min_term} до {loan_type.max_term} мес.\n\n"
            "Введите сумму кредита:",
            reply_markup=get_admin_nav_keyboard(),
            parse_mode=ParseMode.HTML
        )
        await callback.message.answer(
            "Введите сумму кредита:",
            reply_markup=types.ForceReply(selective=True)
        )
        await callback.answer()

    except Exception as e:
        logging.error(f"Ошибка при выборе типа кредита: {e}")
        await callback.message.edit_text(
            "⚠ Ошибка при обработке запроса",
            reply_markup=get_admin_nav_keyboard()
        )
        await callback.answer()

@router.message(F.reply_to_message & F.reply_to_message.text == "Введите сумму кредита:")
async def process_loan_amount(message: types.Message, state: FSMContext):
    """
    Обработка суммы кредита и запрос срока.
    """
    try:
        amount = Decimal(message.text.replace(',', '.'))
        data = await state.get_data()

        if amount < data['min_amount'] or amount > data['max_amount']:
            return await message.answer(
                f"❌ Сумма должна быть от {data['min_amount']} до {data['max_amount']} руб."
            )

        await state.update_data(amount=float(amount))

        await message.answer(
            f"💵 Сумма: {amount:.2f} руб.\n"
            f"⏳ Введите срок кредита (от {data['min_term']} до {data['max_term']} мес.):",
            reply_markup=types.ForceReply(selective=True)
        )

    except ValueError:
        await message.answer("❌ Введите корректную сумму")
    except Exception as e:
        logging.error(f"Ошибка ввода суммы: {e}")
        await message.answer("⚠ Ошибка при обработке запроса")

@router.message(F.reply_to_message & F.reply_to_message.text.startswith("⏳ Введите срок кредита"))
async def process_loan_term(message: types.Message, state: FSMContext):
    """
    Обработка срока кредита и подтверждение.
    """
    try:
        term = int(message.text)
        data = await state.get_data()

        if term < data['min_term'] or term > data['max_term']:
            return await message.answer(
                f"❌ Срок должен быть от {data['min_term']} до {data['max_term']} месяцев"
            )

        monthly_payment = calculate_monthly_payment(
            Decimal(data['amount']),
            term,
            data['interest_rate']
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Подтвердить", callback_data="admin_confirm_loan"),
                    InlineKeyboardButton(text="❌ Отменить", callback_data="admin_cancel_loan")
                ]
            ]
        )

        await message.answer(
            f"📋 <b>Детали кредита:</b>\n\n"
            f"• Клиент ID: {data['client_id']}\n"
            f"• Сумма: {data['amount']:.2f} руб.\n"
            f"• Срок: {term} мес.\n"
            f"• Процентная ставка: {data['interest_rate']}%\n"
            f"• Ежемесячный платеж: ~{monthly_payment:.2f} руб.\n\n"
            "Подтвердить оформление?",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        await state.update_data(term=term)

    except ValueError:
        await message.answer("❌ Введите корректное число месяцев")
    except Exception as e:
        logging.error(f"Ошибка ввода срока: {e}")
        await message.answer("⚠ Ошибка при обработке запроса")

@router.callback_query(F.data == "admin_confirm_loan")
async def confirm_loan(callback: types.CallbackQuery, state: FSMContext):
    """
    Подтверждение и оформление кредита.
    """
    async with async_session() as session:
        try:
            data = await state.get_data()
            client_id = data['client_id']
            client = await session.get(Client, client_id)
            if not client:
                return await callback.message.edit_text(
                    "❌ Клиент не найден",
                    reply_markup=get_admin_nav_keyboard()
                )

            new_loan = Loan(
                client_id=client_id,
                loan_type_id=data['loan_type_id'],
                issue_date=datetime.utcnow(),
                amount=Decimal(data['amount']),
                term=data['term'],
                status=LoanStatus.ACTIVE,
                total_paid=Decimal('0.00'),
                remaining_amount=Decimal(data['amount'])
            )
            session.add(new_loan)
            await session.flush()

            from db_handlers import generate_payment_schedule
            payments = await generate_payment_schedule(
                loan_id=new_loan.loan_id,
                amount=Decimal(data['amount']),
                term=data['term'],
                interest_rate=data['interest_rate'],
                start_date=datetime.utcnow().date(),
                session=session
            )
            for payment in payments:
                session.add(payment)

            client.creditScore = min(1000, client.creditScore + 10)
            await session.commit()

            monthly_payment = calculate_monthly_payment(
                Decimal(data['amount']),
                data['term'],
                data['interest_rate']
            )
            csv_file = generate_payments_csv(payments, new_loan.loan_id)

            await callback.message.edit_text(
                "✅ <b>Кредит успешно оформлен!</b>\n\n"
                f"• Номер кредита: #{new_loan.loan_id}\n"
                f"• Клиент ID: {client_id}\n"
                f"• Сумма: {data['amount']} руб.\n"
                f"• Срок: {data['term']} мес.\n"
                f"• Ежемесячный платеж: {monthly_payment:.2f} руб.",
                reply_markup=get_admin_nav_keyboard(),
                parse_mode=ParseMode.HTML
            )
            await callback.message.answer_document(csv_file)

        except Exception as e:
            await session.rollback()
            logging.error(f"Ошибка оформления кредита: {e}")
            await callback.message.edit_text(
                "⚠ Ошибка при оформлении кредита",
                reply_markup=get_admin_nav_keyboard()
            )
        finally:
            await state.clear()
        await callback.answer()

@router.callback_query(F.data == "admin_cancel_loan")
async def cancel_loan(callback: types.CallbackQuery, state: FSMContext):
    """
    Отмена оформления кредита.
    """
    await callback.message.edit_text(
        "❌ Оформление кредита отменено",
        reply_markup=get_admin_nav_keyboard()
    )
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "admin_make_payment")
async def make_payment_start(callback: types.CallbackQuery):
    """
    Начало процесса приёма платежа.
    """
    await callback.message.edit_text(
        "💸 Введите ID клиента и номер кредита через пробел:\n"
        "<i>Пример: 42 123</i>",
        reply_markup=get_admin_nav_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.message.answer(
        "Введите ID клиента и номер кредита:",
        reply_markup=types.ForceReply(selective=True)
    )
    await callback.answer()

@router.message(F.reply_to_message & F.reply_to_message.text.startswith("Введите ID клиента и номер кредита:"))
async def process_payment_info(message: types.Message, state: FSMContext):
    """
    Обработка ID клиента и номера кредита для платежа.
    """
    try:
        client_id, loan_id = map(int, message.text.split())
    except:
        return await message.answer("❌ Неверный формат. Пример: <code>42 123</code>", parse_mode=ParseMode.HTML)

    async with async_session() as session:
        loan = await session.get(Loan, loan_id)
        if not loan or loan.client_id != client_id or loan.status not in [LoanStatus.ACTIVE, LoanStatus.OVERDUE]:
            return await message.answer("❌ Кредит не найден или недоступен для платежа")

        payment = await session.scalar(
            select(Payment)
            .where(Payment.loan_id == loan_id)
            .where(Payment.payment_date_fact.is_(None))
            .order_by(Payment.payment_date_plan.asc())
        )
        if not payment:
            return await message.answer("❌ Нет платежей для погашения")

        penalty_amount = Decimal(str(payment.penalty_amount or 0))
        total_due = Decimal(str(payment.planned_amount)) + penalty_amount

        await state.update_data(
            client_id=client_id,
            loan_id=loan_id,
            payment_id=payment.payment_id,
            min_payment=float(total_due)
        )

        await message.answer(
            f"💳 Кредит #{loan_id}\n"
            f"📅 Следующий платеж: {payment.payment_date_plan.strftime('%d.%m.%Y')}\n"
            f"💰 Сумма: {payment.planned_amount:.2f} руб.\n"
            f"⚠ Пени: {penalty_amount:.2f} руб.\n"
            f"➡ Итого: {total_due:.2f} руб.\n\n"
            "Введите сумму платежа:",
            reply_markup=types.ForceReply(selective=True),
            parse_mode=ParseMode.HTML
        )

@router.message(F.reply_to_message & F.reply_to_message.text.startswith("Введите сумму платежа:"))
async def process_payment_amount(message: types.Message, state: FSMContext):
    """
    Обработка суммы платежа с возможностью перерасчёта.
    """
    try:
        amount = Decimal(message.text)
        data = await state.get_data()
        min_payment = Decimal(str(data['min_payment']))

        if amount < min_payment:
            return await message.answer(
                f"❌ Сумма меньше необходимого платежа ({min_payment:.2f} руб.)"
            )

        async with async_session() as session:
            loan = await session.get(Loan, data['loan_id'])
            payment = await session.get(Payment, data['payment_id'])

            payment.payment_date_fact = date.today()
            payment.actual_amount = float(amount)
            loan.total_paid += amount
            loan.remaining_amount -= amount

            if amount > min_payment:
                payments = await session.scalars(
                    select(Payment)
                    .where(Payment.loan_id == data['loan_id'])
                    .where(Payment.payment_date_fact.is_(None))
                    .order_by(Payment.payment_date_plan)
                )
                remaining_payments = list(payments)
                if remaining_payments:
                    remaining_term = len(remaining_payments)
                    new_monthly_payment = (loan.remaining_amount / remaining_term).quantize(Decimal('0.01'))
                    for p in remaining_payments:
                        p.planned_amount = float(new_monthly_payment)

            if loan.remaining_amount <= 0:
                loan.status = LoanStatus.CLOSED
                loan.remaining_amount = Decimal('0')
                await session.execute(
                    update(Payment)
                    .where(Payment.loan_id == data['loan_id'])
                    .where(Payment.payment_date_fact.is_(None))
                    .values(payment_date_fact=date.today(), actual_amount=0)
                )

            next_payment = await session.scalar(
                select(Payment)
                .where(Payment.loan_id == data['loan_id'])
                .where(Payment.payment_date_fact.is_(None))
                .order_by(Payment.payment_date_plan.asc())
            )
            loan.next_payment_date = next_payment.payment_date_plan if next_payment else None

            await session.commit()

        await message.answer(
            f"✅ Платеж на сумму {amount:.2f} руб. зачислен!\n"
            f"💳 Остаток по кредиту #{data['loan_id']}: {loan.remaining_amount:.2f} руб.",
            reply_markup=get_admin_nav_keyboard(),
            parse_mode=ParseMode.HTML
        )
        await state.clear()

    except ValueError:
        await message.answer("❌ Введите корректную сумму")
    except Exception as e:
        logging.error(f"Ошибка при обработке платежа: {e}")
        await message.answer("⚠ Ошибка при обработке платежа")

@router.callback_query(F.data == "admin_early_repayment")
async def early_repayment_start(callback: types.CallbackQuery):
    """
    Начало процесса досрочного погашения.
    """
    await callback.message.edit_text(
        "🔄 Введите ID клиента и номер кредита через пробел:\n"
        "<i>Пример: 42 123</i>",
        reply_markup=get_admin_nav_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.message.answer(
        "Введите ID клиента и номер кредита:",
        reply_markup=types.ForceReply(selective=True)
    )
    await callback.answer()

@router.message(F.reply_to_message & F.reply_to_message.text.startswith("Введите ID клиента и номер кредита:"))
async def process_early_repayment_info(message: types.Message, state: FSMContext):
    """
    Обработка ID клиента и номера кредита для досрочного погашения.
    """
    try:
        client_id, loan_id = map(int, message.text.split())
    except:
        return await message.answer("❌ Неверный формат. Пример: <code>42 123</code>", parse_mode=ParseMode.HTML)

    async with async_session() as session:
        loan = await session.get(Loan, loan_id, options=[joinedload(Loan.loan_type)])
        if not loan or loan.client_id != client_id or loan.status not in [LoanStatus.ACTIVE, LoanStatus.OVERDUE]:
            return await message.answer("❌ Кредит не найден или недоступен")

        await state.update_data(
            client_id=client_id,
            loan_id=loan_id,
            remaining_amount=float(loan.remaining_amount),
            interest_rate=loan.loan_type.interest_rate
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Уменьшить платежи",
                        callback_data="admin_reduce_payment"
                    ),
                    InlineKeyboardButton(
                        text="Сократить срок",
                        callback_data="admin_reduce_term"
                    )
                ]
            ]
        )

        await message.answer(
            f"💳 Кредит #{loan_id}\n"
            f"💰 Остаток: {loan.remaining_amount:.2f} руб.\n\n"
            "Выберите тип досрочного погашения:",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )

@router.callback_query(F.data.in_(["admin_reduce_payment", "admin_reduce_term"]))
async def process_early_repayment_type(callback: types.CallbackQuery, state: FSMContext):
    """
    Обработка типа досрочного погашения.
    """
    repayment_type = "reduce_payment" if callback.data == "admin_reduce_payment" else "reduce_term"
    await state.update_data(repayment_type=repayment_type)

    await callback.message.edit_text(
        "💰 Введите сумму досрочного погашения:",
        reply_markup=get_admin_nav_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.message.answer(
        "Введите сумму:",
        reply_markup=types.ForceReply(selective=True)
    )
    await callback.answer()

@router.message(F.reply_to_message & F.reply_to_message.text == "Введите сумму:")
async def process_early_repayment_amount(message: types.Message, state: FSMContext):
    """
    Обработка суммы досрочного погашения.
    """
    try:
        amount = Decimal(message.text)
        data = await state.get_data()

        if amount <= 0:
            return await message.answer("❌ Сумма должна быть больше нуля")

        async with async_session() as session:
            loan = await session.get(Loan, data['loan_id'], options=[joinedload(Loan.loan_type)])
            if amount > loan.remaining_amount:
                amount = loan.remaining_amount

            early_payment = Payment(
                loan_id=data['loan_id'],
                payment_date_plan=date.today(),
                planned_amount=float(amount),
                payment_date_fact=date.today(),
                actual_amount=float(amount),
                is_early_payment=True
            )
            session.add(early_payment)
            loan.remaining_amount -= amount
            loan.total_paid += amount

            await session.execute(
                update(Payment)
                .where(Payment.loan_id == data['loan_id'])
                .where(Payment.payment_date_fact.is_(None))
                .values(payment_date_fact=date.today(), actual_amount=0)
            )

            if loan.remaining_amount <= 0:
                loan.status = LoanStatus.CLOSED
                loan.next_payment_date = None
                await session.commit()
                await message.answer(
                    f"✅ Кредит #{data['loan_id']} полностью погашен!\n"
                    f"💰 Сумма: {amount:.2f} руб.",
                    reply_markup=get_admin_nav_keyboard(),
                    parse_mode=ParseMode.HTML
                )
                await state.clear()
                return

            payments = await session.scalars(
                select(Payment)
                .where(Payment.loan_id == data['loan_id'])
                .where(Payment.payment_date_fact.is_(None))
                .order_by(Payment.payment_date_plan)
            )
            remaining_payments = list(payments)
            remaining_term = len(remaining_payments)

            from db_handlers import generate_payment_schedule
            if data['repayment_type'] == "reduce_payment":
                new_payments = await generate_payment_schedule(
                    loan_id=data['loan_id'],
                    amount=loan.remaining_amount,
                    term=remaining_term,
                    interest_rate=data['interest_rate'],
                    start_date=date.today(),
                    session=session
                )
                new_monthly_payment = Decimal(str(new_payments[0].planned_amount)) if new_payments else Decimal('0')
                response = (
                    f"✅ Досрочное погашение на {amount:.2f} руб. зачислено!\n"
                    f"💳 Кредит #{data['loan_id']}\n"
                    f"💰 Остаток: {loan.remaining_amount:.2f} руб.\n"
                    f"📅 Новый платеж: {new_monthly_payment:.2f} руб."
                )
            else:
                original_term = loan.term
                original_amount = Decimal(str(loan.amount))
                paid_ratio = (original_amount - loan.remaining_amount) / original_amount
                new_term = max(1, round(remaining_term * (1 - paid_ratio)))
                new_payments = await generate_payment_schedule(
                    loan_id=data['loan_id'],
                    amount=loan.remaining_amount,
                    term=new_term,
                    interest_rate=data['interest_rate'],
                    start_date=date.today(),
                    session=session
                )
                new_monthly_payment = Decimal(str(new_payments[0].planned_amount)) if new_payments else Decimal('0')
                response = (
                    f"✅ Досрочное погашение на {amount:.2f} руб. зачислено!\n"
                    f"💳 Кредит #{data['loan_id']}\n"
                    f"💰 Остаток: {loan.remaining_amount:.2f} руб.\n"
                    f"📅 Новый срок: {new_term} мес.\n"
                    f"💸 Платеж: {new_monthly_payment:.2f} руб."
                )

            for p in new_payments:
                session.add(p)

            next_payment = await session.scalar(
                select(Payment)
                .where(Payment.loan_id == data['loan_id'])
                .where(Payment.payment_date_fact.is_(None))
                .order_by(Payment.payment_date_plan.asc())
            )
            loan.next_payment_date = next_payment.payment_date_plan if next_payment else None

            await session.commit()

        await message.answer(
            response,
            reply_markup=get_admin_nav_keyboard(),
            parse_mode=ParseMode.HTML
        )
        await state.clear()

    except ValueError:
        await message.answer("❌ Введите корректную сумму")
    except Exception as e:
        logging.error(f"Ошибка при досрочном погашении: {e}")
        await message.answer("⚠ Ошибка при обработке запроса")

@router.callback_query(F.data == "admin_reports")
async def reports_menu(callback: types.CallbackQuery):
    """
    Меню выбора отчётов.
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📜 Справка об обязательствах",
                    callback_data="admin_report_no_obligations"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚖ Повестка в суд",
                    callback_data="admin_report_court_notice"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 Годовой отчёт",
                    callback_data="admin_report_annual"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        "📈 Выберите тип отчёта:",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data == "admin_report_no_obligations")
async def report_no_obligations(callback: types.CallbackQuery):
    """
    Генерация справки об отсутствии обязательств.
    """
    await callback.message.edit_text(
        "📜 Введите ID клиента для справки об отсутствии обязательств:",
        reply_markup=get_admin_nav_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.message.answer(
        "Введите ID клиента:",
        reply_markup=types.ForceReply(selective=True)
    )
    await callback.answer()

@router.message(F.reply_to_message & F.reply_to_message.text == "Введите ID клиента:")
async def process_no_obligations_report(message: types.Message):
    """
    Обработка ID клиента и генерация справки.
    """
    if not message.text.isdigit():
        return await message.answer("❌ ID должен быть числом")

    client_id = int(message.text)
    async with async_session() as session:
        client = await session.get(Client, client_id)
        if not client:
            return await message.answer("❌ Клиент не найден")

        active_loans = await session.scalar(
            select(func.count(Loan.loan_id))
            .where(
                and_(
                    Loan.client_id == client_id,
                    Loan.status.in_([LoanStatus.ACTIVE, LoanStatus.OVERDUE])
                )
            )
        )
        if active_loans > 0:
            return await message.answer(
                "❌ У клиента есть непогашенные кредиты. Справка не может быть выдана."
            )

    report_content = (
        f"Справка об отсутствии обязательств\n\n"
        f"Клиент: {client.fullName}\n"
        f"ID клиента: {client_id}\n"
        f"Дата: {datetime.now().strftime('%d.%m.%Y')}\n\n"
        "Настоящим подтверждается, что по состоянию на указанную дату "
        "у клиента отсутствуют непогашенные кредитные обязательства."
    )

    from io import BytesIO
    report_file = BytesIO(report_content.encode('utf-8'))
    report_file.name = f"no_obligations_{client_id}.txt"

    await message.answer_document(
        types.BufferedInputFile(
            report_file.getvalue(),
            filename=report_file.name
        ),
        caption="📜 Справка об отсутствии обязательств",
        reply_markup=get_admin_nav_keyboard()
    )

@router.callback_query(F.data == "admin_report_court_notice")
async def report_court_notice(callback: types.CallbackQuery):
    """
    Генерация повестки в суд.
    """
    await callback.message.edit_text(
        "⚖ Введите ID клиента для повестки в суд:",
        reply_markup=get_admin_nav_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.message.answer(
        "Введите ID клиента:",
        reply_markup=types.ForceReply(selective=True)
    )
    await callback.answer()

@router.message(F.reply_to_message & F.reply_to_message.text == "Введите ID клиента:")
async def process_court_notice_report(message: types.Message):
    """
    Обработка ID клиента и генерация повестки.
    """
    if not message.text.isdigit():
        return await message.answer("❌ ID должен быть числом")

    client_id = int(message.text)
    async with async_session() as session:
        client = await session.get(Client, client_id)
        if not client:
            return await message.answer("❌ Клиент не найден")

        overdue_payments = await session.scalar(
            select(func.count(Payment.payment_id))
            .where(
                Payment.loan_id.in_(
                    select(Loan.loan_id)
                    .where(Loan.client_id == client_id)
                    .where(Loan.status == LoanStatus.OVERDUE)
                )
            )
            .where(Payment.payment_date_fact.is_(None))
            .where(Payment.payment_date_plan < date.today())
        )
        if overdue_payments < 3:
            return await message.answer(
                "❌ У клиента недостаточно просрочек для повестки (требуется 3+)"
            )

        total_debt = await session.scalar(
            select(func.sum(Loan.remaining_amount))
            .where(Loan.client_id == client_id)
            .where(Loan.status == LoanStatus.OVERDUE)
        )
        total_debt = total_debt or Decimal('0')

    report_content = (
        f"Повестка в суд\n\n"
        f"Клиент: {client.fullName}\n"
        f"ID клиента: {client_id}\n"
        f"Дата: {datetime.now().strftime('%d.%m.%Y')}\n\n"
        f"Уважаемый(ая) {client.fullName},\n"
        "В связи с неоднократным нарушением условий кредитного договора "
        f"(просрочено {overdue_payments} платежей, общая задолженность: {total_debt:.2f} руб.), "
        "вызываетесь в суд для рассмотрения дела о взыскании задолженности.\n"
        "Дата заседания: [Указать дату]\n"
        "Адрес суда: [Указать адрес]"
    )

    from io import BytesIO
    report_file = BytesIO(report_content.encode('utf-8'))
    report_file.name = f"court_notice_{client_id}.txt"

    await message.answer_document(
        types.BufferedInputFile(
            report_file.getvalue(),
            filename=report_file.name
        ),
        caption="⚖ Повестка в суд",
        reply_markup=get_admin_nav_keyboard()
    )

@router.callback_query(F.data == "admin_report_annual")
async def report_annual(callback: types.CallbackQuery):
    """
    Генерация годового финансового отчёта.
    """
    async with async_session() as session:
        year = datetime.now().year - 1
        total_loans = await session.scalar(
            select(func.count(Loan.loan_id))
            .where(func.extract('year', Loan.issue_date) == year)
        )
        total_amount = await session.scalar(
            select(func.sum(Loan.amount))
            .where(func.extract('year', Loan.issue_date) == year)
        )
        total_payments = await session.scalar(
            select(func.sum(Payment.actual_amount))
            .where(func.extract('year', Payment.payment_date_fact) == year)
        )
        total_penalties = await session.scalar(
            select(func.sum(Payment.penalty_amount))
            .where(func.extract('year', Payment.penalty_date) == year)
        )

        total_amount = total_amount or Decimal('0')
        total_payments = total_payments or Decimal('0')
        total_penalties = total_penalties or Decimal('0')

    report_content = (
        f"Годовой финансовый отчёт за {year} год\n\n"
        f"Дата формирования: {datetime.now().strftime('%d.%m.%Y')}\n\n"
        f"• Выдано кредитов: {total_loans}\n"
        f"• Общая сумма кредитов: {total_amount:.2f} руб.\n"
        f"• Погашено: {total_payments:.2f} руб.\n"
        f"• Начислено пеней: {total_penalties:.2f} руб."
    )

    from io import BytesIO
    report_file = BytesIO(report_content.encode('utf-8'))
    report_file.name = f"annual_report_{year}.txt"

    await callback.message.edit_text(
        f"📅 Годовой отчёт за {year} сформирован",
        reply_markup=get_admin_nav_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.message.answer_document(
        types.BufferedInputFile(
            report_file.getvalue(),
            filename=report_file.name
        ),
        caption=f"📅 Годовой отчёт за {year}"
    )
    await callback.answer()
