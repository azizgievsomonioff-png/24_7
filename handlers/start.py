from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.queries import upsert_user
from keyboards.main_menu import main_menu_keyboard

router = Router()

WELCOME = (
    "Здравствуйте! Я помогу создать продающую карточку товара для маркетплейса: "
    "SEO, описание, характеристики, структуру инфографики и промты для слайдов.\n\n"
    "Выберите действие:"
)


async def show_main_menu(message: Message) -> None:
    await message.answer(WELCOME, reply_markup=main_menu_keyboard())


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    await upsert_user(user.id, user.username, user.first_name)
    await show_main_menu(message)


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer(WELCOME, reply_markup=main_menu_keyboard())
    await callback.answer()


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Текущий сценарий отменен.", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "cancel_flow")
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Текущий сценарий отменен.", reply_markup=main_menu_keyboard())
    await callback.answer()
