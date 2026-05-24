import json
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.queries import get_project, update_project_result
from keyboards.chatgpt_prompts import slide_prompt_keyboard
from keyboards.result_actions import result_actions_keyboard
from services.ai_generator import AIGenerator
from services.openai_prompt_service import (
    generate_marketplace_prompts,
    regenerate_slide_prompt,
    revise_slide_prompt,
)
from services.project_storage import save_project
from states.card_states import CardStates, ChatGptPromptStates
from utils.text import chunk_text, h

router = Router()
logger = logging.getLogger(__name__)


def _chatgpt_to_result(product_data: dict, prompt_result: dict) -> dict:
    base_result = AIGenerator().generate_card(product_data)
    slides = prompt_result["slides"]
    base_result["seo_titles"] = {
        "short": prompt_result["seo_title"],
        "medium": prompt_result["seo_title"],
        "full": prompt_result["seo_title"],
    }
    base_result["description"] = prompt_result["short_description"]
    base_result["infographic_plan"] = [
        {
            "slide": slide["slide_number"],
            "title": slide["title"],
            "goal": slide["goal"],
            "visual": "AI-промт ChatGPT для маркетплейсной инфографики 3:4",
            "text": slide.get("text_on_slide", []),
        }
        for slide in slides
    ]
    base_result["image_prompts"] = [
        {
            "slide": slide["slide_number"],
            "prompt": slide["image_prompt"],
            "title": slide["title"],
            "goal": slide["goal"],
            "text_on_slide": slide.get("text_on_slide", []),
        }
        for slide in slides
    ]
    base_result["chatgpt_prompt_result"] = prompt_result
    return base_result


def _result_to_prompt_result(result: dict) -> dict:
    if result.get("chatgpt_prompt_result"):
        return result["chatgpt_prompt_result"]
    seo = result.get("seo_titles", {})
    prompts_by_slide = {item.get("slide"): item for item in result.get("image_prompts", [])}
    slides = []
    for item in result.get("infographic_plan", []):
        prompt_item = prompts_by_slide.get(item.get("slide"), {})
        slides.append(
            {
                "slide_number": item.get("slide"),
                "title": item.get("title", ""),
                "goal": item.get("goal", ""),
                "text_on_slide": item.get("text", []),
                "image_prompt": prompt_item.get("prompt", ""),
            }
        )
    return {
        "seo_title": seo.get("full") or seo.get("medium") or seo.get("short") or "",
        "short_description": result.get("description", ""),
        "slides": slides,
    }


async def _send_prompt_result(message: Message, project_id: int, prompt_result: dict) -> None:
    await message.answer(
        f"<b>SEO-название</b>\n{h(prompt_result['seo_title'])}\n\n"
        f"<b>Короткое описание</b>\n{h(prompt_result['short_description'])}"
    )
    for slide in prompt_result["slides"]:
        await _send_slide(message, project_id, slide)
    await message.answer("Промты ChatGPT сохранены в проекте. Их можно использовать для генерации картинок.", reply_markup=result_actions_keyboard(project_id))


async def _send_slide(message: Message, project_id: int, slide: dict) -> None:
    text = (
        f"<b>Слайд {h(slide['slide_number'])}: {h(slide['title'])}</b>\n\n"
        f"<b>Цель</b>\n{h(slide['goal'])}\n\n"
        "<b>Текст на слайде</b>\n"
        + "\n".join(f"• {h(item)}" for item in slide.get("text_on_slide", []))
        + f"\n\n<b>Промт для изображения</b>\n{h(slide['image_prompt'])}"
    )
    for chunk in chunk_text(text):
        await message.answer(chunk, reply_markup=slide_prompt_keyboard(project_id, int(slide["slide_number"])))


async def _load_project_data(project_id: int, telegram_id: int) -> tuple[dict, dict] | tuple[None, None]:
    project = await get_project(project_id, telegram_id)
    if not project:
        return None, None
    product_data = json.loads(project["product_data_json"])
    return project, product_data


async def _save_prompt_result(project_id: int, telegram_id: int, project: dict, product_data: dict, prompt_result: dict) -> dict:
    result = _chatgpt_to_result(product_data, prompt_result)
    await update_project_result(project_id, telegram_id, json.dumps(result, ensure_ascii=False))
    return result


@router.callback_query(CardStates.confirm_generation, F.data == "chatgpt_prompts_from_state")
async def generate_chatgpt_from_state(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await callback.message.answer("Отправляю данные товара в ChatGPT и готовлю промты для 6 слайдов...")
    try:
        product_data = await state.get_data()
        prompt_result = await generate_marketplace_prompts(product_data)
        result = _chatgpt_to_result(product_data, prompt_result)
        project_id = await save_project(callback.from_user.id, product_data, result)
        await state.update_data(project_id=project_id, result_json=json.dumps(result, ensure_ascii=False))
        await state.set_state(CardStates.show_result)
        await _send_prompt_result(callback.message, project_id, prompt_result)
    except Exception:
        logger.exception("ChatGPT prompt generation failed")
        await callback.message.answer("Не удалось сгенерировать промты через ChatGPT. Проверьте OPENAI_API_KEY, модель и попробуйте ещё раз.")


@router.callback_query(F.data.startswith("chatgpt_prompts:"))
async def generate_chatgpt_for_project(callback: CallbackQuery) -> None:
    project_id = int(callback.data.split(":", 1)[1])
    await callback.answer()
    project, product_data = await _load_project_data(project_id, callback.from_user.id)
    if not project:
        await callback.message.answer("Проект не найден.")
        return
    await callback.message.answer("Отправляю проект в ChatGPT и обновляю промты...")
    try:
        prompt_result = await generate_marketplace_prompts(product_data)
        await _save_prompt_result(project_id, callback.from_user.id, project, product_data, prompt_result)
        await _send_prompt_result(callback.message, project_id, prompt_result)
    except Exception:
        logger.exception("ChatGPT project prompt generation failed")
        await callback.message.answer("Не удалось сгенерировать промты через ChatGPT. Проверьте OPENAI_API_KEY, модель и попробуйте ещё раз.")


@router.callback_query(F.data.startswith("chatgpt_regen_slide:"))
async def regenerate_slide(callback: CallbackQuery) -> None:
    _, project_id_raw, slide_raw = callback.data.split(":")
    project_id = int(project_id_raw)
    slide_number = int(slide_raw)
    await callback.answer()
    project, product_data = await _load_project_data(project_id, callback.from_user.id)
    if not project:
        await callback.message.answer("Проект не найден.")
        return
    try:
        result = json.loads(project["result_json"])
        prompt_result = _result_to_prompt_result(result)
        old_slide = next(slide for slide in prompt_result["slides"] if int(slide["slide_number"]) == slide_number)
        await callback.message.answer(f"Переделываю слайд {slide_number} через ChatGPT...")
        new_slide = await regenerate_slide_prompt(product_data, old_slide)
        prompt_result["slides"] = [new_slide if int(slide["slide_number"]) == slide_number else slide for slide in prompt_result["slides"]]
        await _save_prompt_result(project_id, callback.from_user.id, project, product_data, prompt_result)
        await _send_slide(callback.message, project_id, new_slide)
    except Exception:
        logger.exception("Slide regeneration failed")
        await callback.message.answer("Не удалось переделать этот слайд. Попробуйте ещё раз.")


@router.callback_query(F.data.startswith("chatgpt_edit_slide:"))
async def ask_slide_revision(callback: CallbackQuery, state: FSMContext) -> None:
    _, project_id_raw, slide_raw = callback.data.split(":")
    await state.set_state(ChatGptPromptStates.waiting_slide_correction)
    await state.update_data(edit_project_id=int(project_id_raw), edit_slide_number=int(slide_raw))
    await callback.message.answer("Напишите правку для этого слайда. Например: «сделай текст короче» или «убери военную тематику».")
    await callback.answer()


@router.message(ChatGptPromptStates.waiting_slide_correction)
async def apply_slide_revision(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    project_id = int(data["edit_project_id"])
    slide_number = int(data["edit_slide_number"])
    project, product_data = await _load_project_data(project_id, message.from_user.id)
    if not project:
        await message.answer("Проект не найден.")
        await state.clear()
        return
    try:
        result = json.loads(project["result_json"])
        prompt_result = _result_to_prompt_result(result)
        old_slide = next(slide for slide in prompt_result["slides"] if int(slide["slide_number"]) == slide_number)
        await message.answer(f"Вношу правку в слайд {slide_number} через ChatGPT...")
        new_slide = await revise_slide_prompt(product_data, old_slide, message.text or "")
        prompt_result["slides"] = [new_slide if int(slide["slide_number"]) == slide_number else slide for slide in prompt_result["slides"]]
        await _save_prompt_result(project_id, message.from_user.id, project, product_data, prompt_result)
        await state.clear()
        await _send_slide(message, project_id, new_slide)
    except Exception:
        logger.exception("Slide revision failed")
        await message.answer("Не удалось применить правку. Попробуйте ещё раз.")


@router.callback_query(F.data.startswith("chatgpt_copy_prompt:"))
async def copy_prompt(callback: CallbackQuery) -> None:
    _, project_id_raw, slide_raw = callback.data.split(":")
    project_id = int(project_id_raw)
    slide_number = int(slide_raw)
    project = await get_project(project_id, callback.from_user.id)
    if not project:
        await callback.message.answer("Проект не найден.")
        await callback.answer()
        return
    result = json.loads(project["result_json"])
    prompt_result = _result_to_prompt_result(result)
    slide = next((slide for slide in prompt_result["slides"] if int(slide["slide_number"]) == slide_number), None)
    if not slide:
        await callback.message.answer("Слайд не найден.")
    else:
        await callback.message.answer(f"<pre>{h(slide['image_prompt'])}</pre>")
    await callback.answer()


@router.callback_query(F.data.startswith("chatgpt_next_slide:"))
async def next_slide(callback: CallbackQuery) -> None:
    _, project_id_raw, slide_raw = callback.data.split(":")
    project_id = int(project_id_raw)
    next_number = int(slide_raw) + 1
    project = await get_project(project_id, callback.from_user.id)
    if not project:
        await callback.message.answer("Проект не найден.")
        await callback.answer()
        return
    prompt_result = _result_to_prompt_result(json.loads(project["result_json"]))
    slide = next((slide for slide in prompt_result["slides"] if int(slide["slide_number"]) == next_number), None)
    if not slide:
        await callback.message.answer("Это последний слайд.")
    else:
        await _send_slide(callback.message, project_id, slide)
    await callback.answer()
