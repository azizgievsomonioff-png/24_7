from utils.text import SKIPPED, clean_text, csv_items


class InfographicGenerator:
    def generate_plan(self, data: dict) -> list[dict]:
        name = clean_text(data.get("product_name"))
        advantage = clean_text(data.get("main_advantage"))
        pains = clean_text(data.get("customer_pains"))
        features = csv_items(data.get("key_features")) or [advantage]
        use_cases = clean_text(data.get("use_cases"))
        complect = clean_text(data.get("size_or_complect"))
        material = clean_text(data.get("material"))

        slides = [
            {
                "slide": 1,
                "title": advantage if advantage != SKIPPED else name,
                "goal": "Выделиться в выдаче и быстро показать главную выгоду.",
                "visual": "Крупное фото товара на чистом фоне, 2-3 коротких бейджа, минимум текста.",
                "text": [item for item in [advantage, data.get("color"), complect] if item and item != SKIPPED][:3],
            },
            {
                "slide": 2,
                "title": "Проблема и решение",
                "goal": "Показать боль покупателя и объяснить, как товар помогает в обычном сценарии.",
                "visual": "Композиция слева/справа: проблема слева, решение справа, простые иконки.",
                "text": [pains if pains != SKIPPED else "Покупателю сложно быстро выбрать подходящий товар", advantage if advantage != SKIPPED else "Понятная практичная выгода"],
            },
            {
                "slide": 3,
                "title": "Детали и преимущества",
                "goal": "Показать конструкцию, материал и ключевые особенности.",
                "visual": "Товар крупно, стрелки-выноски к важным деталям, 4-6 преимуществ.",
                "text": features[:6],
            },
            {
                "slide": 4,
                "title": "Для кого подходит",
                "goal": "Расширить аудиторию и показать сценарии использования.",
                "visual": "Несколько аккуратных зон со сценариями: работа, дом, спорт, авто, подарок или другие контексты.",
                "text": csv_items(use_cases) or [use_cases if use_cases != SKIPPED else "каждый день", "дом", "работа", "подарок"],
            },
        ]
        if complect != SKIPPED or material != SKIPPED:
            slides.append(
                {
                    "slide": 5,
                    "title": "Состав и комплектация",
                    "goal": "Снять вопросы по размеру, материалу или набору.",
                    "visual": "Чистая схема с пиктограммами, крупными цифрами и понятными подписями.",
                    "text": [item for item in [material, complect] if item != SKIPPED],
                }
            )
        if len(features) >= 3 or advantage != SKIPPED:
            slides.append(
                {
                    "slide": len(slides) + 1,
                    "title": "Готово к покупке",
                    "goal": "Закрыть сомнения и мягко подтолкнуть к выбору.",
                    "visual": "Финальный чистый слайд с товаром, короткой выгодой и спокойным призывом.",
                    "text": ["Практичный выбор", "Понятные характеристики", "Добавьте в корзину"],
                }
            )
        return slides[:6]
