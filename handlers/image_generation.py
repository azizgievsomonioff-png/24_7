import json
import logging
from datetime import datetime
from pathlib import Path

from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile

from config import BASE_DIR, settings
from database.queries import get_project, update_project_images
from keyboards.image_actions import image_generation_confirm_keyboard, image_generation_done_keyboard
from services.openai_image_generator import OpenAIImageGenerator, build_marketplace_image_prompt
from services.zip_exporter import create_images_zip

router = Router()
logger = logging.getLogger(__name__)
active_generations: set[int] = set()


def _image_extension() -> str:
    output_format = settings.openai_image_output_format.lower().strip()
    if output_format in {"jpeg", "jpg"}:
        return ".jpg"
    if output_format == "webp":
        return ".webp"
    return ".png"


def _load_images(project: dict) -> list[dict]:
    raw = project.get("generated_images_json") or "[]"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.exception("Invalid generated_images_json for project %s", project.get("id"))
        return []


def _resolve_image_path(image_path: str) -> Path:
    path = Path(image_path)
    return path if path.is_absolute() else BASE_DIR / path


@router.callback_query(F.data.startswith("generate_images:"))
async def ask_generate_images(callback: CallbackQuery) -> None:
    project_id = int(callback.data.split(":", 1)[1])
    project = await get_project(project_id, callback.from_user.id)
    if not project:
        await callback.message.answer("Проект не найден.")
        await callback.answer()
        return
    if not settings.openai_api_key or settings.openai_api_key == "PASTE_OPENAI_API_KEY_HERE":
        await callback.message.answer("Генерация изображений не настроена. Добавьте OPENAI_API_KEY в .env.")
        await callback.answer()
        return

    main_image_path = project.get("main_image_path")
    main_image_file = _resolve_image_path(main_image_path) if main_image_path else None
    warning = "Генерация изображений может расходовать платный OpenAI API. Запустить генерацию?"
    if not main_image_file or not main_image_file.exists():
        warning = (
            "Фото товара не найдено. Я сгенерирую изображение только по описанию. "
            "Товар может отличаться от реального.\n\n"
            "Генерация изображений может расходовать платный OpenAI API. Запустить генерацию?"
        )
    await callback.message.answer(warning, reply_markup=image_generation_confirm_keyboard(project_id))
    await callback.answer()


@router.callback_query(F.data.startswith("image_confirm:"))
async def generate_images(callback: CallbackQuery) -> None:
    telegram_id = callback.from_user.id
    project_id = int(callback.data.split(":", 1)[1])
    if telegram_id in active_generations:
        await callback.message.answer("Генерация уже выполняется. Дождитесь завершения.")
        await callback.answer()
        return
    if not settings.openai_api_key or settings.openai_api_key == "PASTE_OPENAI_API_KEY_HERE":
        await callback.message.answer("Генерация изображений не настроена. Добавьте OPENAI_API_KEY в .env.")
        await callback.answer()
        return

    project = await get_project(project_id, telegram_id)
    if not project:
        await callback.message.answer("Проект не найден.")
        await callback.answer()
        return

    active_generations.add(telegram_id)
    await callback.answer()
    try:
        result = json.loads(project["result_json"])
        prompts = result.get("image_prompts", [])[:6]
        if not prompts:
            await callback.message.answer("В проекте нет промтов для генерации изображений.")
            return

        generator = OpenAIImageGenerator(
            api_key=settings.openai_api_key,
            model=settings.openai_image_model,
            size=settings.openai_image_size,
            quality=settings.openai_image_quality,
            output_format=settings.openai_image_output_format,
            base_url=settings.openai_base_url,
        )
        relative_output_dir = Path("data") / "projects" / str(telegram_id) / str(project_id) / "generated"
        output_dir = BASE_DIR / relative_output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        main_image_path = project.get("main_image_path")
        main_image_file = _resolve_image_path(main_image_path) if main_image_path else None
        use_reference = bool(main_image_file and main_image_file.exists())
        generated: list[dict] = []
        failed: list[int] = []

        for index, item in enumerate(prompts, start=1):
            slide = int(item.get("slide") or index)
            await callback.message.answer(f"Генерирую слайд {index} из {len(prompts)}...")
            enhanced_prompt = build_marketplace_image_prompt(
                base_prompt=item.get("prompt", ""),
                slide_number=slide,
                marketplace=project.get("marketplace") or "",
                product_name=project.get("product_name") or "",
            )
            relative_output_path = relative_output_dir / f"slide_{slide}{_image_extension()}"
            output_path = BASE_DIR / relative_output_path
            try:
                if use_reference:
                    image_path = await generator.generate_image_with_reference(enhanced_prompt, str(main_image_file), str(output_path))
                else:
                    image_path = await generator.generate_image_from_prompt(enhanced_prompt, str(output_path))
                generated.append(
                    {
                        "slide": slide,
                        "prompt": enhanced_prompt,
                        "image_path": str(relative_output_path).replace("\\", "/"),
                        "created_at": datetime.now().isoformat(timespec="seconds"),
                    }
                )
                await callback.message.answer_photo(FSInputFile(image_path), caption=f"Слайд {slide}")
            except FileNotFoundError:
                logger.exception("Reference image is missing")
                failed.append(slide)
                await callback.message.answer(f"Не удалось сгенерировать слайд {slide}. Исходное фото не найдено, попробую следующий.")
            except OSError:
                logger.exception("Failed to save generated image")
                failed.append(slide)
                await callback.message.answer("Не удалось сохранить изображение. Проверьте папку data/projects.")
            except Exception:
                logger.exception("Failed to generate slide %s", slide)
                failed.append(slide)
                await callback.message.answer(f"Не удалось сгенерировать слайд {slide}. Попробую следующий.")

        await update_project_images(project_id, telegram_id, json.dumps(generated, ensure_ascii=False))
        success_slides = [str(item["slide"]) for item in generated]
        report = "Готово! Все изображения сгенерированы." if not failed else "Генерация завершена частично."
        report += f"\nУспешно: {', '.join(success_slides) if success_slides else 'нет'}."
        if failed:
            report += f"\nНе удалось: {', '.join(map(str, failed))}."
        await callback.message.answer(report, reply_markup=image_generation_done_keyboard(project_id))
    except Exception:
        logger.exception("Image generation flow failed")
        await callback.message.answer("Генерация изображений сейчас недоступна. Проверьте OPENAI_API_KEY.")
    finally:
        active_generations.discard(telegram_id)


@router.callback_query(F.data.startswith("show_images:"))
async def show_images(callback: CallbackQuery) -> None:
    project_id = int(callback.data.split(":", 1)[1])
    project = await get_project(project_id, callback.from_user.id)
    if not project:
        await callback.message.answer("Проект не найден.")
        await callback.answer()
        return
    images = _load_images(project)
    existing = [item for item in images if item.get("image_path") and _resolve_image_path(item["image_path"]).exists()]
    if not existing:
        await callback.message.answer("Для этого проекта картинки ещё не сгенерированы.")
        await callback.answer()
        return
    for item in existing:
        await callback.message.answer_photo(FSInputFile(_resolve_image_path(item["image_path"])), caption=f"Слайд {item.get('slide')}")
    await callback.answer()


@router.callback_query(F.data.startswith("zip_images:"))
async def zip_images(callback: CallbackQuery) -> None:
    project_id = int(callback.data.split(":", 1)[1])
    project = await get_project(project_id, callback.from_user.id)
    if not project:
        await callback.message.answer("Проект не найден.")
        await callback.answer()
        return
    images = _load_images(project)
    image_paths = [
        str(_resolve_image_path(item["image_path"]))
        for item in images
        if item.get("image_path") and _resolve_image_path(item["image_path"]).exists()
    ]
    if not images:
        await callback.message.answer("Картинки ещё не сгенерированы. Сначала нажмите 🎨 Сгенерировать картинки.")
        await callback.answer()
        return
    if not image_paths:
        await callback.message.answer("Файлы изображений не найдены. Попробуйте сгенерировать картинки заново.")
        await callback.answer()
        return
    zip_path = BASE_DIR / "data" / "exports" / f"images_{callback.from_user.id}_{project_id}.zip"
    create_images_zip(image_paths, str(zip_path))
    await callback.message.answer_document(FSInputFile(zip_path), caption="ZIP-архив с изображениями готов.")
    await callback.answer()
