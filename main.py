import logging
from aiogram import Bot, Dispatcher
from config import Config
from handlers import basic, db_handlers, admin
from utils.commands import set_bot_commands  # ← Импорт функции
from utils.database import init_db

async def on_startup():
    """Действия при запуске бота"""
    # Инициализация БД (создание таблиц)
    await init_db()
    logging.info("✅ Таблицы в БД успешно созданы/проверены")


async def main():
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=Config.BOT_TOKEN)
    dp = Dispatcher()

    # Установка команд бота
    await set_bot_commands(bot)

    dp.include_routers(
        basic.router,
        db_handlers.router,
        admin.router
    )
    dp.startup.register(on_startup)


    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())