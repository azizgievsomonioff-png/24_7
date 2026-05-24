from utils.text import clean_text


class PromptGenerator:
    def generate_prompts(self, data: dict, plan: list[dict]) -> list[dict]:
        marketplace = clean_text(data.get("marketplace"))
        product = clean_text(data.get("product_name"))
        prompts: list[dict] = []
        for slide in plan:
            badges = slide.get("text", [])[:3]
            badge_text = ", ".join(f'"{badge}"' for badge in badges)
            prompts.append(
                {
                    "slide": slide["slide"],
                    "prompt": (
                        f"Создай инфографику для маркетплейса {marketplace} в формате 3:4.\n"
                        f"Товар: {product}.\n"
                        "Использовать основное фото товара без изменения формы, цвета, пропорций и логотипов.\n"
                        "Фон: чистый светлый фон с аккуратными тенями и достаточным контрастом.\n"
                        f"Композиция: {slide.get('visual')}.\n"
                        f"Заголовок: \"{slide.get('title')}\".\n"
                        f"Текстовые бейджи: {badge_text}.\n"
                        "Стиль: современный маркетплейс, чистый дизайн, высокая читаемость, аккуратные тени, премиальный внешний вид.\n"
                        "Требования: не перегружать слайд текстом, не добавлять лишние надписи, не искажать товар, "
                        "не менять товар, не добавлять несуществующие элементы, все надписи должны быть крупными и читаемыми."
                    ),
                }
            )
        return prompts

    def generate_quick(self, description: str) -> dict:
        data = {
            "marketplace": "универсальная карточка",
            "product_name": description,
            "main_advantage": "главная выгода товара",
            "customer_pains": "покупатель хочет быстро понять пользу товара",
            "key_features": "выгода, качество, удобство, понятная комплектация",
            "use_cases": "каждый день, дом, работа, подарок",
        }
        from services.infographic_generator import InfographicGenerator

        plan = InfographicGenerator().generate_plan(data)[:4]
        return {
            "style": "Чистый маркетплейсный дизайн, формат 3:4, крупный товар, короткие заголовки, читаемые бейджи.",
            "plan": plan,
            "prompts": self.generate_prompts(data, plan),
        }
