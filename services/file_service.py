from pathlib import Path
from uuid import uuid4

from aiogram import Bot
from aiogram.types import Message

BASE_DIR = Path(__file__).resolve().parent.parent


async def save_main_photo(bot: Bot, message: Message) -> str:
    telegram_id = message.from_user.id
    temp_id = uuid4().hex[:12]
    project_dir = BASE_DIR / "data" / "projects" / str(telegram_id) / temp_id
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_dir / "main.jpg"
    photo = message.photo[-1]
    await bot.download(photo.file_id, destination=path)
    return str(path)
