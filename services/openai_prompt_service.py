import asyncio
import base64
import json
import logging
from pathlib import Path
from typing import Any

from config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Ты профессиональный маркетплейс-копирайтер и дизайнер инфографики для Ozon и Wildberries.
Твоя задача — создавать сильные, короткие и продающие промты для генерации инфографики товара.
Ты работаешь с карточками товаров.
Ты должен думать как дизайнер маркетплейса: крупный товар, чистый фон, мало текста, понятные преимущества, 3:4 формат, читаемость на телефоне.
Ты не должен перегружать слайд текстом.
Ты не должен добавлять неподтверждённые свойства.
Ты не должен менять внешний вид товара.
Ты не должен добавлять чужие бренды, флаги, военную символику, запрещённые элементы или агрессивные формулировки.
Тексты должны быть на русском языке.
Промты для генерации изображения должны быть подробными, но без лишней воды.
Каждый слайд должен иметь отдельную идею.
Верни только валидный JSON без markdown.
""".strip()

PROMPT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["seo_title", "short_description", "slides"],
    "properties": {
        "seo_title": {"type": "string"},
        "short_description": {"type": "string"},
        "slides": {
            "type": "array",
            "minItems": 6,
            "maxItems": 6,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["slide_number", "title", "goal", "text_on_slide", "image_prompt"],
                "properties": {
                    "slide_number": {"type": "integer"},
                    "title": {"type": "string"},
                    "goal": {"type": "string"},
                    "text_on_slide": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 4,
                        "items": {"type": "string"},
                    },
                    "image_prompt": {"type": "string"},
                },
            },
        },
    },
}

SLIDE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["slide_number", "title", "goal", "text_on_slide", "image_prompt"],
    "properties": {
        "slide_number": {"type": "integer"},
        "title": {"type": "string"},
        "goal": {"type": "string"},
        "text_on_slide": {"type": "array", "minItems": 1, "maxItems": 4, "items": {"type": "string"}},
        "image_prompt": {"type": "string"},
    },
}


def _client():
    from openai import OpenAI

    if settings.openai_base_url:
        return OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    return OpenAI(api_key=settings.openai_api_key)


def _image_data_url(image_path: str | None) -> str | None:
    if not image_path:
        return None
    path = Path(image_path)
    if not path.exists():
        return None
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _response_text(response) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text
    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                chunks.append(text)
    return "\n".join(chunks)


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    return json.loads(text)


def _validate_prompt_result(data: dict) -> dict:
    slides = data.get("slides")
    if not isinstance(slides, list) or len(slides) != 6:
        raise ValueError("OpenAI response must contain exactly 6 slides")
    for index, slide in enumerate(slides, start=1):
        slide["slide_number"] = int(slide.get("slide_number") or index)
        if not slide.get("image_prompt"):
            raise ValueError(f"Slide {index} has empty image_prompt")
        if not isinstance(slide.get("text_on_slide"), list):
            slide["text_on_slide"] = []
        slide["text_on_slide"] = [str(item).strip() for item in slide["text_on_slide"] if str(item).strip()][:4]
    return data


async def _responses_json(
    user_text: str,
    schema: dict[str, Any],
    schema_name: str,
    image_path: str | None = None,
) -> dict:
    content: list[dict[str, Any]] = [{"type": "input_text", "text": user_text}]
    data_url = _image_data_url(image_path)
    if data_url:
        content.append({"type": "input_image", "image_url": data_url})

    def request() -> str:
        response = _client().responses.create(
            model=settings.openai_text_model,
            input=[
                {"role": "system", "content": [{"type": "input_text", "text": SYSTEM_PROMPT}]},
                {"role": "user", "content": content},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                },
                "verbosity": "medium",
            },
        )
        return _response_text(response)

    raw = await asyncio.to_thread(request)
    try:
        return _parse_json(raw)
    except Exception:
        logger.exception("OpenAI returned invalid JSON, retrying once")
        return await _repair_json(raw, schema, schema_name)


async def _repair_json(raw_text: str, schema: dict[str, Any], schema_name: str) -> dict:
    def request() -> str:
        response = _client().responses.create(
            model=settings.openai_text_model,
            input=[
                {"role": "system", "content": [{"type": "input_text", "text": "Исправь ответ в валидный JSON по схеме. Верни только JSON без markdown."}]},
                {"role": "user", "content": [{"type": "input_text", "text": raw_text}]},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                }
            },
        )
        return _response_text(response)

    fixed = await asyncio.to_thread(request)
    return _parse_json(fixed)


def _product_prompt(product_data: dict) -> str:
    return f"""
Проанализируй товар и создай SEO-название, короткое описание и 6 качественных промтов для инфографики.

Данные товара:
{json.dumps(product_data, ensure_ascii=False, indent=2)}

Логика слайдов:
1. Главный экран — товар + главное преимущество.
2. Комплектация — что входит в набор.
3. Материал — ткань, удобство, практичность.
4. Детали — стрелки-выноски к конструкции.
5. Для кого подходит — сценарии использования.
6. Размеры и финальный призыв.

Правила:
- Формат инфографики: 3:4.
- Язык: русский.
- Текст на слайде короткий, крупный, читаемый на телефоне.
- Не больше 1 заголовка и 2-4 коротких подписей на слайд.
- Не менять цвет, форму, пропорции, логотипы и реальные детали товара.
- Не использовать слова “лучший”, “№1”, “оригинал”, “гарантированно”, если это не подтверждено.
- Не использовать агрессивную военную символику.
- Для мультикам/тактического стиля делай безопасный акцент: активный отдых, охота, рыбалка, страйкбол, полевые выезды.
- Каждый image_prompt должен быть готовым подробным промтом для генерации изображения маркетплейсной инфографики.
""".strip()


async def generate_marketplace_prompts(product_data: dict) -> dict:
    if not settings.openai_api_key or settings.openai_api_key == "PASTE_OPENAI_API_KEY_HERE":
        raise RuntimeError("OPENAI_API_KEY is not configured")
    result = await _responses_json(
        user_text=_product_prompt(product_data),
        schema=PROMPT_SCHEMA,
        schema_name="marketplace_prompts",
        image_path=product_data.get("main_image_path"),
    )
    return _validate_prompt_result(result)


async def regenerate_slide_prompt(product_data: dict, slide: dict) -> dict:
    user_text = f"""
Переделай только один слайд инфографики. Верни JSON только этого слайда.

Данные товара:
{json.dumps(product_data, ensure_ascii=False, indent=2)}

Старый слайд:
{json.dumps(slide, ensure_ascii=False, indent=2)}

Сделай новую версию с той же идеей слайда, но лучше: короче текст, сильнее визуальная композиция, без неподтвержденных заявлений.
""".strip()
    result = await _responses_json(user_text=user_text, schema=SLIDE_SCHEMA, schema_name="marketplace_slide", image_path=product_data.get("main_image_path"))
    return result


async def revise_slide_prompt(product_data: dict, slide: dict, user_revision: str) -> dict:
    user_text = f"""
Обнови только один слайд инфографики по правке пользователя. Верни JSON только этого слайда.

Данные товара:
{json.dumps(product_data, ensure_ascii=False, indent=2)}

Текущий слайд:
{json.dumps(slide, ensure_ascii=False, indent=2)}

Правка пользователя:
{user_revision}

Сохрани безопасность: не добавляй неподтвержденные заявления, не меняй товар, не перегружай текстом.
""".strip()
    result = await _responses_json(user_text=user_text, schema=SLIDE_SCHEMA, schema_name="marketplace_slide_revision", image_path=product_data.get("main_image_path"))
    return result
