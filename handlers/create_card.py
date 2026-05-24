import json
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.categories import categories_keyboard
from keyboards.gender import audience_keyboard
from keyboards.main_menu import main_menu_keyboard
from keyboards.marketplace import marketplace_keyboard
from keyboards.result_actions import confirm_keyboard, result_actions_keyboard
from keyboards.skip import skip_keyboard
from services.ai_generator import AIGenerator
from services.file_service import save_main_photo
from services.project_storage import save_project
from states.card_states import CardStates
from utils.text import chunk_text, clean_text, h

router = Router()


async def start_card_flow(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(CardStates.choose_marketplace)
    await message.answer("Для какой площадки делаем карточку?", reply_markup=marketplace_keyboard())


@router.message(Command("new"))
@router.message(F.text == "🆕 Создать карточку")
async def new_card(message: Message, state: FSMContext) -> None:
    await start_card_flow(message, state)


@router.callback_query(F.data == "new_card")
@router.callback_query(F.data == "restart_card")
async def cb_new_card(callback: CallbackQuery, state: FSMContext) -> None:
    await start_card_flow(callback.message, state)
    await callback.answer()


@router.callback_query(CardStates.choose_marketplace, F.data.startswith("marketplace:"))
async def choose_marketplace(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(marketplace=callback.data.split(":", 1)[1])
    await state.set_state(CardStates.choose_category)
    await callback.message.answer("Какая категория товара?", reply_markup=categories_keyboard())
    await callback.answer()


@router.callback_query(CardStates.choose_category, F.data.startswith("category:"))
async def choose_category(callback: CallbackQuery, state: FSMContext) -> None:
    category = callback.data.split(":", 1)[1]
    if category == "Другое":
        await state.set_state(CardStates.custom_category)
        await callback.message.answer("Введите категорию товара вручную.")
    else:
        await state.update_data(category=category)
        await ask_photo(callback.message, state)
    await callback.answer()


@router.message(CardStates.custom_category)
async def custom_category(message: Message, state: FSMContext) -> None:
    await state.update_data(category=clean_text(message.text))
    await ask_photo(message, state)


async def ask_photo(message: Message, state: FSMContext) -> None:
    await state.set_state(CardStates.upload_photo)
    await message.answer("Отправьте основное фото товара. Оно будет сохранено в проекте.")


@router.message(CardStates.upload_photo)
async def upload_photo(message: Message, state: FSMContext, bot: Bot) -> None:
    if not message.photo:
        await message.answer("Пожалуйста, отправьте именно изображение товара.")
        return
    path = await save_main_photo(bot, message)
    await state.update_data(main_image_path=path)
    await state.set_state(CardStates.product_name)
    await message.answer(
        "Введите название товара. Например: “мужские черные носки 10 пар”, "
        "“масляный фильтр 03C115561H”, “летние рабочие сандалии”."
    )


@router.message(CardStates.product_name)
async def product_name(message: Message, state: FSMContext) -> None:
    await state.update_data(product_name=clean_text(message.text))
    await state.set_state(CardStates.target_audience)
    await message.answer("Для кого товар?", reply_markup=audience_keyboard())


@router.callback_query(CardStates.target_audience, F.data.startswith("audience:"))
async def target_audience(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":", 1)[1]
    if value == "Другое":
        await state.set_state(CardStates.custom_audience)
        await callback.message.answer("Введите аудиторию вручную.")
    else:
        await state.update_data(target_audience="Не указано" if value == "Пропустить" else value)
        await ask_main_advantage(callback.message, state)
    await callback.answer()


@router.message(CardStates.custom_audience)
async def custom_audience(message: Message, state: FSMContext) -> None:
    await state.update_data(target_audience=clean_text(message.text))
    await ask_main_advantage(message, state)


async def ask_main_advantage(message: Message, state: FSMContext) -> None:
    await state.set_state(CardStates.main_advantage)
    await message.answer(
        "Какое главное преимущество товара нужно показать в карточке?\n\n"
        "Примеры: удобная посадка, прочный материал, подходит для жары, выгодный набор, "
        "аналог оригинальной запчасти, премиальный внешний вид.",
        reply_markup=skip_keyboard(),
    )


async def ask_next(message: Message, state: FSMContext, next_state, text: str) -> None:
    await state.set_state(next_state)
    await message.answer(text, reply_markup=skip_keyboard())


async def save_text_or_skip(message: Message, state: FSMContext, key: str, next_state, text: str) -> None:
    await state.update_data(**{key: clean_text(message.text)})
    await ask_next(message, state, next_state, text)


@router.callback_query(F.data == "skip")
async def skip_current(callback: CallbackQuery, state: FSMContext) -> None:
    current = await state.get_state()
    mapping = {
        CardStates.main_advantage.state: ("main_advantage", CardStates.material, "Укажите материал, состав или важные технические детали."),
        CardStates.material.state: ("material", CardStates.color, "Укажите цвет товара."),
        CardStates.color.state: ("color", CardStates.size_or_complect, "Укажите размер, объём, комплектацию или количество в наборе.\n\nПримеры: 10 пар, размер 41–45, 1 штука, комплект из 3 предметов, 250 мл."),
        CardStates.size_or_complect.state: ("size_or_complect", CardStates.use_cases, "Где и как покупатель будет использовать товар?\n\nПримеры: каждый день, работа, спорт, рыбалка, склад, автомобиль, дом, подарок."),
        CardStates.use_cases.state: ("use_cases", CardStates.customer_pains, "Какие проблемы клиента решает товар?\n\nПримеры: ноги потеют, обувь натирает, товар быстро рвётся, неудобно на работе, дорого покупать поштучно."),
        CardStates.customer_pains.state: ("customer_pains", CardStates.key_features, "Напишите 3–5 преимуществ товара через запятую.\n\nПример: мягкая резинка, средняя высота, черный цвет, подходит на каждый день, набор 10 пар"),
    }
    if current == CardStates.key_features.state:
        await state.update_data(key_features="Не указано")
        await show_summary(callback.message, state)
    elif current in mapping:
        key, next_state, text = mapping[current]
        await state.update_data(**{key: "Не указано"})
        await ask_next(callback.message, state, next_state, text)
    await callback.answer()


@router.message(CardStates.main_advantage)
async def main_advantage(message: Message, state: FSMContext) -> None:
    await save_text_or_skip(message, state, "main_advantage", CardStates.material, "Укажите материал, состав или важные технические детали.")


@router.message(CardStates.material)
async def material(message: Message, state: FSMContext) -> None:
    await save_text_or_skip(message, state, "material", CardStates.color, "Укажите цвет товара.")


@router.message(CardStates.color)
async def color(message: Message, state: FSMContext) -> None:
    await save_text_or_skip(message, state, "color", CardStates.size_or_complect, "Укажите размер, объём, комплектацию или количество в наборе.")


@router.message(CardStates.size_or_complect)
async def size_or_complect(message: Message, state: FSMContext) -> None:
    await save_text_or_skip(message, state, "size_or_complect", CardStates.use_cases, "Где и как покупатель будет использовать товар?")


@router.message(CardStates.use_cases)
async def use_cases(message: Message, state: FSMContext) -> None:
    await save_text_or_skip(message, state, "use_cases", CardStates.customer_pains, "Какие проблемы клиента решает товар?")


@router.message(CardStates.customer_pains)
async def customer_pains(message: Message, state: FSMContext) -> None:
    await save_text_or_skip(message, state, "customer_pains", CardStates.key_features, "Напишите 3–5 преимуществ товара через запятую.")


@router.message(CardStates.key_features)
async def key_features(message: Message, state: FSMContext) -> None:
    await state.update_data(key_features=clean_text(message.text))
    await show_summary(message, state)


async def show_summary(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(CardStates.confirm_generation)
    summary = (
        f"<b>Маркетплейс:</b> {h(data.get('marketplace'))}\n"
        f"<b>Категория:</b> {h(data.get('category'))}\n"
        f"<b>Название:</b> {h(data.get('product_name'))}\n"
        f"<b>Аудитория:</b> {h(data.get('target_audience'))}\n"
        f"<b>Главное преимущество:</b> {h(data.get('main_advantage'))}\n"
        f"<b>Материал:</b> {h(data.get('material'))}\n"
        f"<b>Цвет:</b> {h(data.get('color'))}\n"
        f"<b>Комплектация:</b> {h(data.get('size_or_complect'))}\n"
        f"<b>Сценарии:</b> {h(data.get('use_cases'))}\n"
        f"<b>Боли клиента:</b> {h(data.get('customer_pains'))}\n"
        f"<b>Преимущества:</b> {h(data.get('key_features'))}"
    )
    await message.answer(summary, reply_markup=confirm_keyboard())


@router.callback_query(CardStates.confirm_generation, F.data == "generate_card")
async def generate_card(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        data = await state.get_data()
        result = AIGenerator().generate_card(data)
        project_id = await save_project(callback.from_user.id, data, result)
        await state.update_data(project_id=project_id, result_json=json.dumps(result, ensure_ascii=False))
        await state.set_state(CardStates.show_result)
        await send_result(callback.message, result, project_id)
    except Exception:
        logging.exception("Card generation failed")
        await callback.message.answer("Произошла ошибка. Попробуйте ещё раз или вернитесь в главное меню.", reply_markup=main_menu_keyboard())
    finally:
        await callback.answer()


async def send_result(message: Message, result: dict, project_id: int) -> None:
    seo = result["seo_titles"]
    parts = [
        f"<b>SEO-названия</b>\n\nКороткое:\n{h(seo['short'])}\n\nСреднее:\n{h(seo['medium'])}\n\nПолное:\n{h(seo['full'])}",
        f"<b>Описание</b>\n\n{h(result['description'])}",
        "<b>Характеристики</b>\n\n" + "\n".join(f"{h(k)}: {h(v)}" for k, v in result["characteristics"].items()),
        "<b>План инфографики</b>\n\n" + "\n\n".join(
            f"Слайд {s['slide']}: <b>{h(s['title'])}</b>\nЦель: {h(s['goal'])}\nВизуал: {h(s['visual'])}\nТекст: {h(', '.join(s.get('text', [])))}"
            for s in result["infographic_plan"]
        ),
        "<b>Промты для слайдов</b>\n\n" + "\n\n".join(
            f"Слайд {p['slide']}:\n{h(p['prompt'])}" for p in result["image_prompts"]
        ),
    ]
    for part in parts:
        for chunk in chunk_text(part):
            await message.answer(chunk)
    await message.answer("Проект автоматически сохранен. Что делаем дальше?", reply_markup=result_actions_keyboard(project_id))
