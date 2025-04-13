from aiogram.types import BotCommand
from config import Config

async def set_bot_commands(bot, user_id=None):  # Переименовали функцию
    """Устанавливает меню команд в зависимости от роли"""
    commands = [
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="me", description="Мой профиль"),
        BotCommand(command="credit_info", description="Кредитный рейтинг"),
        BotCommand(command="update_contact", description="Изменить контакты")
    ]

    if user_id in Config.ADMINS:
        commands.append(
            BotCommand(command="admin", description="Админ-панель")
        )

    await bot.set_my_commands(commands)