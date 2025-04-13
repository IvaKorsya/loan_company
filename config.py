from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv  # Для загрузки .env
import os
from aiogram.types import BotCommand

# Загружаем переменные из .env
load_dotenv()

class Config:
    # Настройки бота
    BOT_TOKEN = os.getenv("BOT_TOKEN")  # Токен из .env
    DEFAULT_BOT_PROPERTIES = DefaultBotProperties(parse_mode=ParseMode.HTML)  # Разметка сообщений

    # ID-админов и пароль в админку
    ADMINS = [1355436790]  # Telegram ID админов
    ADMIN_PASSWORD = "i_love_db"

    # Настройки PostgreSQL
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST", "localhost")  # По умолчанию localhost
    DB_PORT = os.getenv("DB_PORT", "5432")       # По умолчанию 5432

    USER_COMMANDS = [
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="me", description="Мой профиль"),
        BotCommand(command="credit_info", description="Кредитный рейтинг"),
        BotCommand(command="update_contact", description="Изменить контакты")
    ]

    ADMIN_COMMANDS = [
        BotCommand(command="admin", description="Админ-панель"),
        *USER_COMMANDS  # Админ получает все команды пользователя
    ]

    @property
    def db_url(self):
        """Формирует строку подключения к PostgreSQL"""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"