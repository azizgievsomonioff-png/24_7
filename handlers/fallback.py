from aiogram import Router
from aiogram.types import Message

from keyboards.main_menu import main_menu_keyboard

router = Router()


@router.message()
async def unknown_message(message: Message) -> None:
    await message.answer(
        "Не понял действие. Выберите пункт в главном меню или используйте /cancel.",
        reply_markup=main_menu_keyboard(),
    )
