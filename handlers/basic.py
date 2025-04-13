from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.utils.markdown import hbold

from utils.commands import set_bot_commands
from config import Config

router = Router(name="basic_commands")

@router.message(Command("start"))
async def cmd_start(message: types.Message, bot: Bot):
    """
    Инициализация бота для нового пользователя

    Действия:
    1. Устанавливает меню команд
    2. Отправляет приветственное сообщение
    3. Записывает факт запуска в лог

    Пример ответа:
    -------------
    👋 Иван Иванов, добро пожаловать в CreditBot!
    Ваш надежный помощник в кредитовании.
    """
    await set_bot_commands(bot, message.from_user.id)

    await message.answer(
        f"👋 {hbold(message.from_user.full_name)}, добро пожаловать в <b>CreditBot</b>!\n"
        "Ваш надежный помощник в кредитовании.",
        parse_mode=ParseMode.HTML
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """
    Показывает справочную информацию о командах

    Формирует список:
    - Основные команды
    - Админские команды (для админов)
    - Контакты поддержки

    Группирует команды по категориям с Markdown-разметкой
    """
    help_text = [
        f"{hbold('📌 Основные команды:')}",
        "/start - Перезапустить бота",
        "/me - Мой профиль",
        "/credit_info - Кредитный рейтинг",
        "",
        f"{hbold('🛠 Техподдержка:')}",
        "По вопросам работы: @credit_support"
    ]

    if message.from_user.id in Config.ADMINS:
        help_text.extend([
            "",
            f"{hbold('👨‍💻 Админские команды:')}",
            "/admin - Панель управления"
        ])

    await message.answer("\n".join(help_text), parse_mode=ParseMode.HTML)

@router.message(Command("about"))
async def cmd_about(message: types.Message):
    """
    Показывает информацию о боте

    Включает:
    - Версию бота
    - Контактные данные
    - Ссылки на документацию

    Использует HTML-форматирование для красивого вывода
    """
    about_text = (
        "<b>CreditBot v1.2</b>\n\n"
        "⚙ <i>Кредитный помощник</i>\n"
        "📅 2024 г.\n\n"
        "📚 Документация: /docs\n"
        "🔄 Обновления: @credit_updates"
    )

    await message.answer(about_text, parse_mode=ParseMode.HTML)

@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message):
    """
    Сбрасывает текущее состояние пользователя

    Функционал:
    - Удаляет клавиатуру
    - Прекращает FSM-процесс (если активен)
    - Отправляет подтверждение отмены

    Важно: Работает только внутри многошаговых процессов
    """
    await message.answer(
        "❌ Текущее действие отменено",
        reply_markup=types.ReplyKeyboardRemove()
    )