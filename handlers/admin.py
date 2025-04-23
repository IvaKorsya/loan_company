from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, update, func
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import logging
from decimal import Decimal
import math

from utils.database import async_session
from models.user import Client, Loan
from models.base import LoanStatus, LoanType
from config import Config
from utils.commands import set_bot_commands

router = Router(name="admin_handlers")

async def is_admin(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь администратором.

    Args:
        user_id (int): Telegram ID пользователя.

    Returns:
        bool: True, если пользователь в списке администраторов, иначе False.
    """
    return user_id in Config.ADMINS

# ---- Админские команды ----

@router.message(Command("admin"))
async def admin_auth(message: types.Message):
    """
    Аутентификация администратора.

    Проверяет, имеет ли пользователь права администратора. Если да, запрашивает пароль для входа в админ-панель.

    Args:
        message (types.Message): Сообщение от пользователя.

    Example:
        User: /admin
        Bot: 🔐 Панель администратора
             Введите пароль для доступа:
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
    Основное меню админ-панели.

    Отображает доступные действия администратора через инлайн-кнопки. Обновляет меню команд для администратора.

    Args:
        message (types.Message): Сообщение с паролем.
        bot (Bot): Экземпляр бота для установки команд.

    Example:
        User: i_love_db
        Bot: 🛠 Административная панель
             [📊 Статистика] [👥 Поиск клиента]
             [⚙ Изменить кредитный рейтинг] [💰 Выдать кредит]
             [💸 Принять платеж] [🔄 Перерасчет платежей]
             [📝 Отчеты]
    """
    if not await is_admin(message.from_user.id):
        return await message.answer("❌ Доступ запрещен")

    await set_bot_commands(bot, message.from_user.id)

    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        types.InlineKeyboardButton(text="👥 Поиск клиента", callback_data="admin_find_client"),
        types.InlineKeyboardButton(text="⚙ Изменить кредитный рейтинг", callback_data="admin_change_credit"),
        types.InlineKeyboardButton(text="💰 Выдать кредит", callback_data="admin_issue_loan"),
        types.InlineKeyboardButton(text="💸 Принять платеж", callback_data="admin_process_payment"),
        types.InlineKeyboardButton(text="🔄 Перерасчет платежей", callback_data="admin_recalculate_payments"),
        types.InlineKeyboardButton(text="📝 Отчеты", callback_data="admin_reports")
    )
    builder.adjust(2)

    await message.answer(
        "🛠 <b>Административная панель</b>",
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

# ---- Обработчики инлайн-кнопок ----

@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: types.CallbackQuery):
    """
    Показывает статистику системы.

    Выводит общее количество клиентов, средний кредитный рейтинг и число администраторов.

    Args:
        callback (types.CallbackQuery): Callback-запрос от инлайн-кнопки.

    Example:
        Bot: 📈 Статистика системы
             • Всего клиентов: 100
             • Средний кредитный рейтинг: 650.0
             • Администраторов: 2
    """
    async with async_session() as session:
        clients_count = await session.scalar(select(func.count()).select_from(Client))
        avg_score = await session.scalar(select(func.avg(Client.creditScore)))

    await callback.message.edit_text(
        f"📈 <b>Статистика системы</b>\n\n"
        f"• Всего клиентов: <b>{clients_count}</b>\n"
        f"• Средний кредитный рейтинг: <b>{avg_score:.1f}</b>\n"
        f"• Администраторов: <b>{len(Config.ADMINS)}</b>",
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data == "admin_find_client")
async def find_client(callback: types.CallbackQuery):
    """
    Запрашивает ID клиента для поиска.

    Args:
        callback (types.CallbackQuery): Callback-запрос от инлайн-кнопки.

    Example:
        Bot: 🔍 Введите ID клиента:
    """
    await callback.message.answer(
        "🔍 Введите ID клиента:",
        reply_markup=types.ForceReply(selective=True)
    )

@router.message(F.reply_to_message & F.reply_to_message.text == "🔍 Введите ID клиента:")
async def process_client_id(message: types.Message):
    """
    Обрабатывает ID клиента и показывает информацию.

    Показывает данные клиента: ID, ФИО, телефон и кредитный рейтинг.

    Args:
        message (types.Message): Сообщение с ID клиента.

    Example:
        User: 42
        Bot: 👤 Данные клиента
             • ID: 42
             • ФИО: Иванов Иван Иванович
             • Телефон: +79161234567
             • Кредитный рейтинг: 750
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
        f"• Кредитный рейтинг: <b>{client.creditScore}</b>",
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data == "admin_change_credit")
async def change_credit_start(callback: types.CallbackQuery):
    """
    Запрашивает данные для изменения кредитного рейтинга.

    Args:
        callback (types.CallbackQuery): Callback-запрос от инлайн-кнопки.

    Example:
        Bot: ✏ Введите ID клиента и новый рейтинг через пробел:
             Пример: 42 750
    """
    await callback.message.answer(
        "✏ Введите ID клиента и новый рейтинг через пробел:\n"
        "<i>Пример: 42 750</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=types.ForceReply(selective=True)
    )

@router.message(F.reply_to_message & F.reply_to_message.text.startswith("✏ Введите ID клиента"))
async def process_credit_change(message: types.Message):
    """
    Обрабатывает изменение кредитного рейтинга.

    Проверяет корректность ввода и обновляет рейтинг клиента в базе данных.

    Args:
        message (types.Message): Сообщение с ID клиента и новым рейтингом.

    Example:
        User: 42 750
        Bot: ✅ Кредитный рейтинг клиента 42 изменен на 750
    """
    try:
        client_id, new_score = message.text.split()
        new_score = int(new_score)

        if not 0 <= new_score <= 1000:
            raise ValueError("Рейтинг должен быть от 0 до 1000")
    except ValueError as e:
        return await message.answer(f"❌ Неверный формат или значение: {str(e)}. Пример: <code>42 750</code>", parse_mode=ParseMode.HTML)

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

    await message.answer(f"✅ Кредитный рейтинг клиента {client_id} изменен на {new_score}")

@router.callback_query(F.data == "admin_issue_loan")
async def issue_loan_start(callback: types.CallbackQuery):
    """
    Запрашивает данные для выдачи кредита.

    Args:
        callback (types.CallbackQuery): Callback-запрос от инлайн-кнопки.

    Example:
        Bot: 💰 Введите ID клиента, сумму кредита, срок (в месяцах) и тип кредита через пробел:
             Пример: 42 500000 12 CONSUMER
    """
    await callback.message.answer(
        "💰 Введите ID клиента, сумму кредита, срок (в месяцах) и тип кредита через пробел:\n"
        "<i>Пример: 42 500000 12 CONSUMER</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=types.ForceReply(selective=True)
    )

@router.message(F.reply_to_message & F.reply_to_message.text.startswith("💰 Введите ID клиента"))
async def process_issue_loan(message: types.Message):
    """
    Обрабатывает выдачу кредита.

    Проверяет клиента, наличие активных кредитов, допустимую сумму, рассчитывает аннуитетный платеж
    и создает кредит с графиком платежей.

    Args:
        message (types.Message): Сообщение с данными кредита.

    Example:
        User: 42 500000 12 CONSUMER
        Bot: ✅ Кредит выдан!
             • ID клиента: 42
             • Сумма: 500000 руб.
             • Ежемесячный платеж: 45000.00 руб.
             • Срок: 12 мес.
    """
    try:
        client_id, amount, term, loan_type = message.text.split()
        client_id = int(client_id)
        amount = Decimal(amount)
        term = int(term)
        loan_type = LoanType[loan_type.upper()]
    except (ValueError, KeyError):
        return await message.answer("❌ Неверный формат. Пример: <code>42 500000 12 CONSUMER</code>", parse_mode=ParseMode.HTML)

    async with async_session() as session:
        client = await session.get(Client, client_id)
        if not client:
            return await message.answer("❌ Клиент не найден")

        active_loans = await session.execute(
            select(Loan).where(Loan.client_id == client_id, Loan.status == LoanStatus.ACTIVE)
        )
        if active_loans.scalars().first():
            return await message.answer("❌ У клиента есть непогашенный кредит")

        max_amount = calculate_max_loan_amount(client.creditScore)
        if amount > max_amount:
            return await message.answer(f"❌ Сумма превышает допустимый лимит ({max_amount} руб.)")

        annual_rate = Decimal('0.1')
        monthly_rate = annual_rate / 12
        monthly_payment = calculate_annuity_payment(amount, monthly_rate, term)

        loan = Loan(
            client_id=client_id,
            amount=amount,
            remaining_amount=amount,
            term=term,
            annual_interest_rate=annual_rate,
            monthly_payment=monthly_payment,
            status=LoanStatus.ACTIVE,
            issue_date=datetime.now(),
            type=loan_type,
            payment_schedule=generate_payment_schedule(amount, monthly_payment, term)
        )
        session.add(loan)
        await session.commit()

        await message.answer(
            f"✅ Кредит выдан!\n"
            f"• ID клиента: {client_id}\n"
            f"• Сумма: {amount} руб.\n"
            f"• Ежемесячный платеж: {monthly_payment:.2f} руб.\n"
            f"• Срок: {term} мес."
        )

@router.callback_query(F.data == "admin_process_payment")
async def process_payment_start(callback: types.CallbackQuery):
    """
    Запрашивает данные для обработки платежа.

    Args:
        callback (types.CallbackQuery): Callback-запрос от инлайн-кнопки.

    Example:
        Bot: 💸 Введите ID кредита и сумму платежа через пробел:
             Пример: 123 50000
    """
    await callback.message.answer(
        "💸 Введите ID кредита и сумму платежа через пробел:\n"
        "<i>Пример: 123 50000</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=types.ForceReply(selective=True)
    )

@router.message(F.reply_to_message & F.reply_to_message.text.startswith("💸 Введите ID кредита"))
async def process_payment(message: types.Message):
    """
    Обрабатывает платеж по кредиту.

    Учитывает пени за просрочки, обновляет остаток и график платежей. Поддерживает досрочное погашение.

    Args:
        message (types.Message): Сообщение с ID кредита и суммой платежа.

    Example:
        User: 123 50000
        Bot: ✅ Платеж принят!
             • Сумма: 50000 руб.
             • Пени: 1000 руб.
             • Остаток: 450000 руб.
    """
    try:
        loan_id, payment = message.text.split()
        loan_id = int(loan_id)
        payment = Decimal(payment)
    except ValueError:
        return await message.answer("❌ Неверный формат. Пример: <code>123 50000</code>", parse_mode=ParseMode.HTML)

    async with async_session() as session:
        loan = await session.get(Loan, loan_id)
        if not loan:
            return await message.answer("❌ Кредит не найден")

        if loan.status != LoanStatus.ACTIVE:
            return await message.answer("❌ Кредит не активен")

        schedule = loan.payment_schedule
        current_date = datetime.now()

        overdue_payments = [
            p for p in schedule if p['date'] < current_date and not p['paid']
        ]
        penalty = sum(p['amount'] * Decimal('0.01') * (current_date - p['date']).days for p in overdue_payments)

        total_payment = payment - penalty
        if total_payment < 0:
            return await message.answer(f"❌ Платеж недостаточен для покрытия пени ({penalty} руб.)")

        loan.remaining_amount -= total_payment
        for p in schedule:
            if not p['paid'] and total_payment >= p['amount']:
                p['paid'] = True
                total_payment -= p['amount']
                p['payment_date'] = current_date
            if total_payment <= 0:
                break

        if loan.remaining_amount <= 0:
            loan.status = LoanStatus.CLOSED
            await session.commit()
            await generate_no_obligations_doc(loan)
            return await message.answer("✅ Кредит полностью погашен!")

        if total_payment > 0:
            loan.payment_schedule = recalculate_payment_schedule(loan, total_payment)
        
        await session.commit()

        await message.answer(
            f"✅ Платеж принят!\n"
            f"• Сумма: {payment} руб.\n"
            f"• Пени: {penalty} руб.\n"
            f"• Остаток: {loan.remaining_amount} руб."
        )

@router.callback_query(F.data == "admin_recalculate_payments")
async def recalculate_payments_start(callback: types.CallbackQuery):
    """
    Запрашивает данные для перерасчета платежей.

    Args:
        callback (types.CallbackQuery): Callback-запрос от инлайн-кнопки.

    Example:
        Bot: 🔄 Введите ID кредита для перерасчета платежей:
    """
    await callback.message.answer(
        "🔄 Введите ID кредита для перерасчета платежей:",
        reply_markup=types.ForceReply(selective=True)
    )

@router.message(F.reply_to_message & F.reply_to_message.text.startswith("🔄 Введите ID кредита"))
async def process_recalculate_payments(message: types.Message):
    """
    Перерасчитывает платежи с учетом просрочек.

    Учитывает пени (1% в сутки) и обновляет график платежей. Генерирует повестку в суд при ≥3 просрочках.

    Args:
        message (types.Message): Сообщение с ID кредита.

    Example:
        User: 123
        Bot: ✅ Платежи перерасчитаны!
             • Пени: 5000 руб.
             • Новый остаток: 455000 руб.
    """
    if not message.text.isdigit():
        return await message.answer("❌ ID должен быть числом")

    async with async_session() as session:
        loan = await session.get(Loan, int(message.text))
        if not loan:
            return await message.answer("❌ Кредит не найден")

        schedule = loan.payment_schedule
        current_date = datetime.now()

        overdue_payments = [
            p for p in schedule if p['date'] < current_date and not p['paid']
        ]
        if not overdue_payments:
            return await message.answer("ℹ Нет просроченных платежей")

        penalty = sum(p['amount'] * Decimal('0.01') * (current_date - p['date']).days for p in overdue_payments)
        loan.remaining_amount += penalty

        loan.payment_schedule = recalculate_payment_schedule(loan, Decimal('0'))
        await session.commit()

        if len(overdue_payments) >= 3:
            await generate_court_notice(loan)

        await message.answer(
            f"✅ Платежи перерасчитаны!\n"
            f"• Пени: {penalty} руб.\n"
            f"• Новый остаток: {loan.remaining_amount} руб."
        )

@router.callback_query(F.data == "admin_reports")
async def reports_start(callback: types.CallbackQuery):
    """
    Запрашивает тип отчета.

    Предлагает выбор между справкой о погашении, повесткой в суд и годовым финансовым отчетом.

    Args:
        callback (types.CallbackQuery): Callback-запрос от инлайн-кнопки.

    Example:
        Bot: 📝 Выберите тип отчета:
             [📄 Справка о погашении]
             [⚖ Повестка в суд]
             [📅 Фин. отчет за год]
    """
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text="📄 Справка о погашении", callback_data="report_no_obligations"),
        types.InlineKeyboardButton(text="⚖ Повестка в суд", callback_data="report_court_notice"),
        types.InlineKeyboardButton(text="📅 Фин. отчет за год", callback_data="report_annual")
    )
    builder.adjust(1)

    await callback.message.answer(
        "📝 Выберите тип отчета:",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data == "report_no_obligations")
async def report_no_obligations_start(callback: types.CallbackQuery):
    """
    Запрашивает ID кредита для справки о погашении.

    Args:
        callback (types.CallbackQuery): Callback-запрос от инлайн-кнопки.

    Example:
        Bot: 📄 Введите ID кредита для справки о погашении:
    """
    await callback.message.answer(
        "📄 Введите ID кредита для справки о погашении:",
        reply_markup=types.ForceReply(selective=True)
    )

@router.message(F.reply_to_message & F.reply_to_message.text.startswith("📄 Введите ID кредита"))
async def process_no_obligations_report(message: types.Message):
    """
    Генерирует справку об отсутствии обязательств.

    Проверяет, что кредит погашен, и формирует справку.

    Args:
        message (types.Message): Сообщение с ID кредита.

    Example:
        User: 123
        Bot: ✅ Справка сформирована!
    """
    if not message.text.isdigit():
        return await message.answer("❌ ID должен быть числом")

    async with async_session() as session:
        loan = await session.get(Loan, int(message.text))
        if not loan or loan.status != LoanStatus.CLOSED:
            return await message.answer("❌ Кредит не найден или не погашен")

        await generate_no_obligations_doc(loan)
        await message.answer("✅ Справка сформирована!")

@router.callback_query(F.data == "report_court_notice")
async def report_court_notice_start(callback: types.CallbackQuery):
    """
    Запрашивает ID кредита для повестки в суд.

    Args:
        callback (types.CallbackQuery): Callback-запрос от инлайн-кнопки.

    Example:
        Bot: ⚖ Введите ID кредита для повестки в суд:
    """
    await callback.message.answer(
        "⚖ Введите ID кредита для повестки в суд:",
        reply_markup=types.ForceReply(selective=True)
    )

@router.message(F.reply_to_message & F.reply_to_message.text.startswith("⚖ Введите ID кредита"))
async def process_court_notice_report(message: types.Message):
    """
    Генерирует повестку в суд.

    Формирует документ для клиента с просроченными платежами.

    Args:
        message (types.Message): Сообщение с ID кредита.

    Example:
        User: 123
        Bot: ✅ Повестка сформирована!
    """
    if not message.text.isdigit():
        return await message.answer("❌ ID должен быть числом")

    async with async_session() as session:
        loan = await session.get(Loan, int(message.text))
        if not loan:
            return await message.answer("❌ Кредит не найден")

        await generate_court_notice(loan)
        await message.answer("✅ Повестка сформирована!")

@router.callback_query(F.data == "report_annual")
async def report_annual_start(callback: types.CallbackQuery):
    """
    Запрашивает год для финансового отчета.

    Args:
        callback (types.CallbackQuery): Callback-запрос от инлайн-кнопки.

    Example:
        Bot: 📅 Введите год для финансового отчета:
             Пример: 2024
    """
    await callback.message.answer(
        "📅 Введите год для финансового отчета:\n"
        "<i>Пример: 2024</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=types.ForceReply(selective=True)
    )

@router.message(F.reply_to_message & F.reply_to_message.text.startswith("📅 Введите год"))
async def process_annual_report(message: types.Message):
    """
    Генерирует финансовый отчет за год.

    Показывает сумму выданных кредитов, погашенных сумм и начисленных пеней за указанный год.

    Args:
        message (types.Message): Сообщение с годом.

    Example:
        User: 2024
        Bot: 📊 Финансовый отчет за 2024 год
             • Выдано кредитов: 10000000 руб.
             • Погашено: 5000000 руб.
             • Пени: 50000 руб.
    """
    if not message.text.isdigit():
        return await message.answer("❌ Год должен быть числом")

    year = int(message.text)
    async with async_session() as session:
        loans = await session.execute(
            select(Loan).where(
                func.extract('year', Loan.issue_date) == year
            )
        )
        loans = loans.scalars().all()

        total_issued = sum(loan.amount for loan in loans)
        total_repaid = sum(
            sum(p['amount'] for p in loan.payment_schedule if p['paid'])
            for loan in loans
        )
        penalties = sum(
            sum(p['amount'] * Decimal('0.01') * (datetime.now() - p['date']).days
                for p in loan.payment_schedule
                if not p['paid'] and p['date'] < datetime.now())
            for loan in loans
        )

        report = (
            f"📊 <b>Финансовый отчет за {year} год</b>\n\n"
            f"• Выдано кредитов: {total_issued} руб.\n"
            f"• Погашено: {total_repaid} руб.\n"
            f"• Пени: {penalties} руб."
        )

        await message.answer(report, parse_mode=ParseMode.HTML)

# ---- Вспомогательные функции ----

def calculate_max_loan_amount(credit_score: int) -> Decimal:
    """
    Определяет максимальную сумму кредита по кредитному рейтингу.

    Args:
        credit_score (int): Кредитный рейтинг клиента (0–1000).

    Returns:
        Decimal: Максимальная сумма кредита в рублях.

    Example:
        >>> calculate_max_loan_amount(850)
        Decimal('1000000')
    """
    if credit_score >= 800:
        return Decimal('1000000')
    elif credit_score >= 600:
        return Decimal('500000')
    elif credit_score >= 400:
        return Decimal('200000')
    else:
        return Decimal('50000')

def calculate_annuity_payment(principal: Decimal, monthly_rate: Decimal, term: int) -> Decimal:
    """
    Рассчитывает аннуитетный платеж.

    Args:
        principal (Decimal): Основная сумма кредита.
        monthly_rate (Decimal): Месячная процентная ставка.
        term (int): Срок кредита в месяцах.

    Returns:
        Decimal: Размер ежемесячного платежа.

    Example:
        >>> calculate_annuity_payment(Decimal('500000'), Decimal('0.008333'), 12)
        Decimal('45000.00')
    """
    if monthly_rate == 0:
        return principal / term
    x = (1 + monthly_rate) ** term
    return principal * (monthly_rate * x) / (x - 1)

def generate_payment_schedule(principal: Decimal, monthly_payment: Decimal, term: int) -> list:
    """
    Генерирует график платежей.

    Args:
        principal (Decimal): Основная сумма кредита.
        monthly_payment (Decimal): Ежемесячный платеж.
        term (int): Срок кредита в месяцах.

    Returns:
        list: Список словарей с датами, суммами и статусом платежей.

    Example:
        >>> generate_payment_schedule(Decimal('500000'), Decimal('45000'), 12)
        [{'date': ..., 'amount': Decimal('45000'), 'paid': False, 'payment_date': None}, ...]
    """
    schedule = []
    remaining = principal
    current_date = datetime.now()

    for i in range(term):
        schedule.append({
            'date': current_date + timedelta(days=30 * (i + 1)),
            'amount': monthly_payment,
            'paid': False,
            'payment_date': None
        })
        remaining -= monthly_payment
        if remaining <= 0:
            break

    return schedule

def recalculate_payment_schedule(loan: Loan, extra_payment: Decimal) -> list:
    """
    Перерасчитывает график платежей.

    Учитывает дополнительный платеж или просрочки для обновления графика.

    Args:
        loan (Loan): Объект кредита.
        extra_payment (Decimal): Дополнительный платеж для перерасчета.

    Returns:
        list: Новый график платежей.

    Example:
        >>> recalculate_payment_schedule(loan, Decimal('10000'))
        [{'date': ..., 'amount': Decimal('43000'), 'paid': False, 'payment_date': None}, ...]
    """
    remaining = loan.remaining_amount - extra_payment
    monthly_rate = loan.annual_interest_rate / 12
    remaining_term = sum(1 for p in loan.payment_schedule if not p['paid'])

    if remaining_term <= 0 or remaining <= 0:
        return loan.payment_schedule

    new_monthly_payment = calculate_annuity_payment(remaining, monthly_rate, remaining_term)
    current_date = datetime.now()

    new_schedule = [
        p for p in loan.payment_schedule if p['paid']
    ]
    for i in range(remaining_term):
        new_schedule.append({
            'date': current_date + timedelta(days=30 * (i + 1)),
            'amount': new_monthly_payment,
            'paid': False,
            'payment_date': None
        })

    return new_schedule

async def generate_no_obligations_doc(loan: Loan):
    """
    Генерирует справку об отсутствии обязательств.

    Формирует текстовую справку для погашенного кредита.

    Args:
        loan (Loan): Объект кредита.

    Example:
        Bot: 📄 Справка об отсутствии обязательств
             • Клиент: Иванов Иван Иванович
             • Кредит №123
             • Сумма: 500000 руб.
             • Дата закрытия: 23.04.2025
             • Статус: Погашен
    """
    async with async_session() as session:
        client = await session.get(Client, loan.client_id)
        doc = (
            f"📄 <b>Справка об отсутствии обязательств</b>\n\n"
            f"• Клиент: {client.fullName}\n"
            f"• Кредит №{loan.loan_id}\n"
            f"• Сумма: {loan.amount} руб.\n"
            f"• Дата закрытия: {datetime.now().strftime('%d.%m.%Y')}\n"
            f"• Статус: Погашен"
        )
        logging.info(f"Справка для кредита {loan.loan_id} сформирована")

async def generate_court_notice(loan: Loan):
    """
    Генерирует повестку в суд.

    Формирует текстовую повестку для клиента с просроченными платежами.

    Args:
        loan (Loan): Объект кредита.

    Example:
        Bot: ⚖ Повестка в суд
             • Клиент: Иванов Иван Иванович
             • Кредит №123
             • Просроченная сумма: 150000 руб.
             • Количество просрочек: 3
             • Дата: 23.04.2025
    """
    async with async_session() as session:
        client = await session.get(Client, loan.client_id)
        overdue_payments = [p for p in loan.payment_schedule if not p['paid'] and p['date'] < datetime.now()]
        total_overdue = sum(p['amount'] for p in overdue_payments)
        doc = (
            f"⚖ <b>Повестка в суд</b>\n\n"
            f"• Клиент: {client.fullName}\n"
            f"• Кредит №{loan.loan_id}\n"
            f"• Просроченная сумма: {total_overdue} руб.\n"
            f"• Количество просрочек: {len(overdue_payments)}\n"
            f"• Дата: {datetime.now().strftime('%d.%m.%Y')}"
        )
        logging.info(f"Повестка для кредита {loan.loan_id} сформирована")
