from services.infographic_generator import InfographicGenerator
from services.prompt_generator import PromptGenerator
from services.seo_generator import SeoGenerator
from utils.text import SKIPPED, clean_text, csv_items


MARKETPLACE_STYLE = {
    "Ozon": "больше SEO, четкие преимущества и понятные характеристики",
    "Wildberries": "эмоциональные короткие выгоды и сильный первый слайд",
    "Avito": "простая человеческая подача, акцент на практичность и выгоду",
    "Яндекс.Маркет": "аккуратный стиль, ясные характеристики и спокойная аргументация",
}


class AIGenerator:
    """Replace this facade with an OpenAI or another AI provider later."""

    def __init__(self) -> None:
        self.seo = SeoGenerator()
        self.infographic = InfographicGenerator()
        self.prompts = PromptGenerator()

    def generate_card(self, data: dict) -> dict:
        titles = self.seo.generate_titles(data)
        plan = self.infographic.generate_plan(data)
        prompts = self.prompts.generate_prompts(data, plan)
        return {
            "seo_titles": titles,
            "description": self._description(data),
            "characteristics": self._characteristics(data),
            "infographic_plan": plan,
            "image_prompts": prompts,
            "designer_task": self._designer_task(data, plan),
        }

    def _description(self, data: dict) -> str:
        name = clean_text(data.get("product_name"))
        advantage = clean_text(data.get("main_advantage"))
        features = csv_items(data.get("key_features"))
        use_cases = clean_text(data.get("use_cases"))
        material = clean_text(data.get("material"))
        complect = clean_text(data.get("size_or_complect"))
        marketplace = clean_text(data.get("marketplace"))
        style = MARKETPLACE_STYLE.get(marketplace, "понятные выгоды и спокойный маркетплейсный стиль")

        p1 = f"{name} — практичный товар для карточки, где покупателю важно быстро понять пользу, назначение и отличие от похожих предложений."
        p2 = f"Главный акцент: {advantage.lower() if advantage != SKIPPED else style}. " + (
            "Дополнительные преимущества: " + ", ".join(features[:5]) + "." if features else "Преимущества лучше показать короткими тезисами и наглядной инфографикой."
        )
        p3 = f"Товар подойдет для сценариев: {use_cases.lower()}." if use_cases != SKIPPED else "Покажите основные сценарии использования на отдельных слайдах, чтобы покупателю было проще представить товар в жизни."
        p4 = " ".join(
            part
            for part in [
                f"Материал или состав: {material}." if material != SKIPPED else "",
                f"Комплектация или размер: {complect}." if complect != SKIPPED else "",
            ]
            if part
        ) or "Характеристики стоит подать ясно: без лишних обещаний, спорных заявлений и мелкого текста."
        p5 = "Добавьте товар в корзину, если вам нужен понятный и практичный вариант с прозрачными характеристиками."
        return "\n\n".join([p1, p2, p3, p4, p5])

    def _characteristics(self, data: dict) -> dict[str, str]:
        return {
            "Площадка": clean_text(data.get("marketplace")),
            "Категория": clean_text(data.get("category")),
            "Название товара": clean_text(data.get("product_name")),
            "Пол / аудитория": clean_text(data.get("target_audience")),
            "Цвет": clean_text(data.get("color")),
            "Материал": clean_text(data.get("material")),
            "Комплектация": clean_text(data.get("size_or_complect")),
            "Назначение": clean_text(data.get("main_advantage")),
            "Сценарии использования": clean_text(data.get("use_cases")),
            "Главное преимущество": clean_text(data.get("main_advantage")),
            "Дополнительные особенности": clean_text(data.get("key_features")),
        }

    def _designer_task(self, data: dict, plan: list[dict]) -> str:
        lines = [
            f"1. Товар: {clean_text(data.get('product_name'))}",
            f"2. Площадка: {clean_text(data.get('marketplace'))}",
            f"3. Категория: {clean_text(data.get('category'))}",
            f"4. Целевая аудитория: {clean_text(data.get('target_audience'))}",
            "5. Основной визуальный стиль: современный маркетплейс, чистая композиция, крупный товар, минимум шума.",
            f"6. Цветовая гамма: учитывать цвет товара ({clean_text(data.get('color'))}), фон светлый или нейтральный.",
            "7. Формат изображений: вертикальный 3:4, пригодный для карточек маркетплейсов.",
            "8. Общие требования: крупные заголовки, читаемые бейджи, аккуратные тени, единая сетка на всех слайдах.",
        ]
        for slide in plan:
            lines.append(f"{8 + slide['slide']}. Слайд {slide['slide']}: {slide['title']} — {slide['goal']} Визуал: {slide['visual']}")
        lines.append(
            "14. Запреты: не искажать товар; не менять цвет товара; не добавлять лишние элементы; "
            "не использовать мелкий текст; не перегружать слайд; не использовать чужие бренды; "
            "не использовать неподтвержденные заявления; не писать \"оригинал\", если это не подтверждено; "
            "не писать \"лучший\", \"№1\", \"лечит\", \"гарантированно\", если это нельзя доказать."
        )
        return "\n".join(lines)
