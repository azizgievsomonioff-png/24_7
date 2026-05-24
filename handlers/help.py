from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

HELP_TEXT = (
    "Я помогу собрать текстовую основу карточки товара:\n\n"
    "• /new — создать карточку с фото и анкетой\n"
    "• /projects — открыть последние проекты\n"
    "• /cancel — отменить текущий сценарий\n\n"
    "MVP генерирует SEO, описание, характеристики, план инфографики, промты и ТЗ для дизайнера. "
    "Готовые картинки на этом этапе не создаются."
)


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
