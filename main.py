import logging
from aiogram import Bot, Dispatcher
from config import Config
from handlers import basic, db_handlers, admin
from utils.commands import set_bot_commands
from utils.database import init_db, async_session
from utils.data_filler import add_default_loan_types
from aiohttp import ClientSession

async def on_startup(bot: Bot):
    await init_db()
    async with async_session() as session:
        await add_default_loan_types(session)
    logging.info("Bot startup completed")

async def main():
    logging.basicConfig(level=logging.DEBUG)  # Установлен DEBUG для отладки

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

    # Создаём ClientSession для aiogram
    async with ClientSession() as http_session:
        try:
            await dp.start_polling(bot, http_session=http_session)
        finally:
            # Гарантируем завершение всех задач
            await dp.fsm.storage.close()
            await bot.session.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
