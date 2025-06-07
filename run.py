import asyncio
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram import Dispatcher
from config import config
from handlers import user

async def main():
    bot = Bot(
    token=config.bot_token,
    default=DefaultBotProperties(parse_mode="HTML")
)
    dp = Dispatcher()
    dp.include_router(user.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())