import json

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database.queries import delete_project, get_project, list_user_projects
from keyboards.result_actions import delete_confirm_keyboard, project_actions_keyboard
from utils.text import chunk_text, h

router = Router()


@router.message(Command("projects"))
@router.message(F.text == "📦 Мои проекты")
async def my_projects(message: Message) -> None:
    projects = await list_user_projects(message.from_user.id)
    if not projects:
        await message.answer("У вас пока нет сохраненных проектов.")
        return
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{p['product_name']} — {p['marketplace']} — {p['created_at'][:10]}", callback_data=f"project:{p['id']}")]
            for p in projects
        ]
    )
    await message.answer("Последние 10 проектов:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("project:"))
async def project_details(callback: CallbackQuery) -> None:
    project_id = int(callback.data.split(":", 1)[1])
    project = await get_project(project_id, callback.from_user.id)
    if not project:
        await callback.message.answer("Проект не найден.")
        await callback.answer()
        return
    await callback.message.answer(
        f"<b>{h(project['product_name'])}</b>\n"
        f"Площадка: {h(project['marketplace'])}\n"
        f"Категория: {h(project['category'])}\n"
        f"Дата: {h(project['created_at'])}",
        reply_markup=project_actions_keyboard(project_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("open_project:"))
async def open_project(callback: CallbackQuery) -> None:
    project_id = int(callback.data.split(":", 1)[1])
    project = await get_project(project_id, callback.from_user.id)
    if not project:
        await callback.message.answer("Проект не найден.")
        await callback.answer()
        return
    result = json.loads(project["result_json"])
    seo = result["seo_titles"]
    text = (
        f"<b>SEO</b>\nКороткое: {h(seo['short'])}\nСреднее: {h(seo['medium'])}\nПолное: {h(seo['full'])}\n\n"
        f"<b>Описание</b>\n{h(result['description'])}\n\n"
        "<b>План инфографики</b>\n"
        + "\n".join(f"Слайд {s['slide']}: {h(s['title'])}" for s in result["infographic_plan"])
    )
    for chunk in chunk_text(text):
        await callback.message.answer(chunk)
    await callback.answer()


@router.callback_query(F.data.startswith("delete_project:"))
async def ask_delete(callback: CallbackQuery) -> None:
    project_id = int(callback.data.split(":", 1)[1])
    await callback.message.answer("Вы уверены, что хотите удалить проект?", reply_markup=delete_confirm_keyboard(project_id))
    await callback.answer()


@router.callback_query(F.data.startswith("delete_confirm:"))
async def confirm_delete(callback: CallbackQuery) -> None:
    project_id = int(callback.data.split(":", 1)[1])
    ok = await delete_project(project_id, callback.from_user.id)
    await callback.message.answer("Проект удален." if ok else "Проект не найден.")
    await callback.answer()
