import json
from pathlib import Path

from database.queries import get_project

BASE_DIR = Path(__file__).resolve().parent.parent


def _section(title: str, body: str) -> str:
    return f"\n\n{title}\n{'=' * len(title)}\n{body}"


def render_result_txt(project: dict) -> str:
    data = json.loads(project["product_data_json"])
    result = json.loads(project["result_json"])
    lines = [
        "Карточка товара для маркетплейса",
        f"Дата создания: {project['created_at']}",
        f"Маркетплейс: {project['marketplace']}",
        f"Категория: {project['category']}",
        f"Название товара: {project['product_name']}",
    ]
    seo = result["seo_titles"]
    lines.append(_section("SEO-названия", f"Короткое: {seo['short']}\nСреднее: {seo['medium']}\nПолное: {seo['full']}"))
    lines.append(_section("Описание", result["description"]))
    chars = "\n".join(f"{key}: {value}" for key, value in result["characteristics"].items())
    lines.append(_section("Характеристики", chars))
    plan = "\n\n".join(
        f"Слайд {s['slide']}: {s['title']}\nЦель: {s['goal']}\nВизуал: {s['visual']}\nТекст: {', '.join(s.get('text', []))}"
        for s in result["infographic_plan"]
    )
    lines.append(_section("План слайдов", plan))
    prompts = "\n\n".join(f"Слайд {p['slide']}:\n{p['prompt']}" for p in result["image_prompts"])
    lines.append(_section("Промты для слайдов", prompts))
    lines.append(_section("ТЗ для дизайнера", result["designer_task"]))
    generated_images = json.loads(project.get("generated_images_json") or "[]")
    if generated_images:
        images_text = "\n\n".join(
            f"Слайд {item.get('slide')}:\n{item.get('image_path')}" for item in generated_images
        )
    else:
        images_text = "Изображения ещё не сгенерированы."
    lines.append(_section("Сгенерированные изображения", images_text))
    if data.get("main_image_path"):
        lines.append(_section("Фото", f"Основное фото сохранено: {data['main_image_path']}"))
    return "\n".join(lines)


async def export_project_to_txt(project_id: int, telegram_id: int) -> Path | None:
    project = await get_project(project_id, telegram_id)
    if not project:
        return None
    export_dir = BASE_DIR / "data" / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    path = export_dir / f"{telegram_id}_{project_id}.txt"
    path.write_text(render_result_txt(project), encoding="utf-8")
    return path
