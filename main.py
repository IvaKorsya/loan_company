import logging
from aiogram import Bot, Dispatcher
from config import Config
from handlers import basic, db_handlers, admin
from utils.commands import set_bot_commands  # ← Импорт функции

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

    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())