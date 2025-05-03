from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, update, func
from utils.commands import set_bot_commands
import sqlalchemy
from datetime import date

from utils.database import async_session
from models.user import Client
from config import Config
from utils.generate_reports import generate_no_obligations_doc, generate_court_notice, generate_annual_financial_report

router = Router(name="admin_handlers")

# Проверка админских прав
async def is_admin(user_id: int) -> bool:
    '''
    Проверка на право администрирования.
    '''
    return user_id in Config.ADMINS

# ---- Админские команды ----

@router.message(Command("admin"))
async def admin_auth(message: types.Message):
    """Аутентификация администратора"""
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
    """Основное меню админки с обновлением команд"""
    if not await is_admin(message.from_user.id):
        return

    await set_bot_commands(bot, message.from_user.id)

    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        types.InlineKeyboardButton(text="👥 Поиск клиента", callback_data="admin_find_client"),
        types.InlineKeyboardButton(text="⚙ Изменить кредитный рейтинг", callback_data="admin_change_credit"),
        types.InlineKeyboardButton(text="📜 Документ об обязательствах", callback_data="admin_no_obligations"),
        types.InlineKeyboardButton(text="⚖ Повестка в суд", callback_data="admin_court_notice"),
        types.InlineKeyboardButton(text="📅 Финансовый отчет", callback_data="admin_financial_report")
    )
    builder.adjust(2)  # Две кнопки в ряд

    await message.answer(
        "🛠 <b>Административная панель</b>",
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.HTML
    )

# ---- Обработчики инлайн-кнопок ----

@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: types.CallbackQuery):
    """Показывает статистику"""
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
    """Поиск клиента по ID"""
    await callback.message.answer(
        "🔍 Введите ID клиента:",
        reply_markup=types.ForceReply(selective=True)
    )

@router.message(F.reply_to_message & F.reply_to_message.text == "🔍 Введите ID клиента:")
async def process_client_id(message: types.Message):
    """Обработка ID клиента"""
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
    """Изменение кредитного рейтинга"""
    await callback.message.answer(
        "✏ Введите ID клиента и новый рейтинг через пробел:\n"
        "<i>Пример: 42 750</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=types.ForceReply(selective=True)
    )

@router.message(F.reply_to_message & F.reply_to_message.text.startswith("✏ Введите ID клиента"))
async def process_credit_change(message: types.Message):
    """Обработка изменения рейтинга"""
    try:
        client_id, new_score = message.text.split()
        new_score = int(new_score)

        if not 0 <= new_score <= 1000:
            raise ValueError
    except:
        return await message.answer("❌ Неверный формат. Пример: <code>42 750</code>", parse_mode=ParseMode.HTML)

    async with async_session() as session:
        await session.execute(
            update(Client)
            .where(Client.clientID == int(client_id))
            .values(creditScore=new_score)
        )
        await session.commit()

    await message.answer(f"✅ Кредитный рейтинг клиента {client_id} изменен на {new_score}")

@router.callback_query(F.data == "admin_no_obligations")
async def no_obligations_start(callback: types.CallbackQuery):
    """Запрос ID кредита для документа об отсутствии обязательств"""
    await callback.message.answer(
        "📜 Введите ID кредита для формирования документа об отсутствии обязательств:",
        reply_markup=types.ForceReply(selective=True)
    )

@router.message(F.reply_to_message & F.reply_to_message.text.startswith("📜 Введите ID кредита"))
async def process_no_obligations(message: types.Message):
    """Обработка ID кредита для документа об отсутствии обязательств"""
    if not message.text.isdigit():
        return await message.answer("❌ ID должен быть числом")

    async with async_session() as session:
        doc_text = await generate_no_obligations_doc(int(message.text), session)

    if not doc_text:
        return await message.answer("❌ Кредит не найден или не погашен")

    await message.answer(doc_text, parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "admin_court_notice")
async def court_notice_start(callback: types.CallbackQuery):
    """Запрос ID кредита для повестки в суд"""
    await callback.message.answer(
        "⚖ Введите ID кредита для формирования повестки в суд:",
        reply_markup=types.ForceReply(selective=True)
    )

@router.message(F.reply_to_message & F.reply_to_message.text.startswith("⚖ Введите ID кредита"))
async def process_court_notice(message: types.Message):
    """Обработка ID кредита для повестки в суд"""
    if not message.text.isdigit():
        return await message.answer("❌ ID должен быть числом")

    async with async_session() as session:
        notice_text = await generate_court_notice(int(message.text), session)

    if not notice_text:
        return await message.answer("❌ Кредит не найден или недостаточно просроченных платежей (<3)")

    await message.answer(notice_text, parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "admin_financial_report")
async def financial_report_start(callback: types.CallbackQuery):
    """Запрос года для финансового отчета"""
    await callback.message.answer(
        "📅 Введите год для формирования финансового отчета (например, 2024):",
        reply_markup=types.ForceReply(selective=True)
    )

@router.message(F.reply_to_message & F.reply_to_message.text.startswith("📅 Введите год"))
async def process_financial_report(message: types.Message):
    """Обработка года для финансового отчета"""
    if not message.text.isdigit():
        return await message.answer("❌ Год должен быть числом")

    year = int(message.text)
    if year < 2000 or year > date.today().year:
        return await message.answer("❌ Неверный год")

    async with async_session() as session:
        report_text = await generate_annual_financial_report(year, session)

    await message.answer(report_text, parse_mode=ParseMode.HTML)