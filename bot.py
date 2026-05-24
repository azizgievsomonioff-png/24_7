import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from database.db import init_db
from handlers import chatgpt_prompts, create_card, export, fallback, help, image_generation, projects, seo, start
from utils.logger import setup_logging


async def main() -> None:
    setup_logging()
    if not settings.bot_token or settings.bot_token == "PASTE_TELEGRAM_BOT_TOKEN_HERE":
        raise RuntimeError("BOT_TOKEN is not configured. Copy .env.example to .env and paste Telegram bot token.")

    await init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(help.router)
    dp.include_router(create_card.router)
    dp.include_router(seo.router)
    dp.include_router(projects.router)
    dp.include_router(export.router)
    dp.include_router(chatgpt_prompts.router)
    dp.include_router(image_generation.router)
    dp.include_router(fallback.router)

    logging.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
