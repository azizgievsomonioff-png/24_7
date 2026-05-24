from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from services.prompt_generator import PromptGenerator
from services.seo_generator import SeoGenerator
from states.card_states import PromptStates, SeoStates
from utils.text import h

router = Router()


@router.message(F.text == "✍️ SEO для карточки")
async def seo_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SeoStates.waiting_query)
    await message.answer(
        "Введите товар, категорию и важные ключевые слова.\n\n"
        "Например:\nмужские носки черные 10 пар, средняя высота, хлопок, на каждый день"
    )


@router.message(SeoStates.waiting_query)
async def seo_generate(message: Message, state: FSMContext) -> None:
    result = SeoGenerator().generate_quick(message.text or "")
    text = (
        "<b>5 вариантов SEO-названия</b>\n"
        + "\n".join(f"{i}. {h(title)}" for i, title in enumerate(result["titles"], 1))
        + "\n\n<b>20 ключевых фраз</b>\n"
        + "\n".join(f"• {h(item)}" for item in result["phrases"])
        + "\n\n<b>20 хештегов</b>\n"
        + " ".join(h(item) for item in result["hashtags"])
        + f"\n\n<b>Короткое описание</b>\n{h(result['description'])}"
        + "\n\n<b>Преимущества</b>\n"
        + "\n".join(f"• {h(item)}" for item in result["advantages"])
    )
    await state.clear()
    await message.answer(text)


@router.message(F.text == "🖼 Промты для инфографики")
async def prompts_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(PromptStates.waiting_description)
    await message.answer("Опишите товар и что нужно показать на карточке.")


@router.message(PromptStates.waiting_description)
async def prompts_generate(message: Message, state: FSMContext) -> None:
    result = PromptGenerator().generate_quick(message.text or "")
    plan = "\n\n".join(
        f"Слайд {s['slide']}: <b>{h(s['title'])}</b>\n{h(s['goal'])}\n{h(s['visual'])}"
        for s in result["plan"]
    )
    prompts = "\n\n".join(f"Слайд {p['slide']}:\n{h(p['prompt'])}" for p in result["prompts"])
    await state.clear()
    await message.answer(f"<b>Общий стиль</b>\n{h(result['style'])}\n\n<b>Структура на 4 слайда</b>\n{plan}\n\n<b>Промты</b>\n{prompts}")
