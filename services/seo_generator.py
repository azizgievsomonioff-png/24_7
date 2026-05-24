from utils.text import SKIPPED, clean_text, csv_items, is_skipped


AUDIENCE_SHORT = {
    "Для мужчин": "мужские",
    "Для женщин": "женские",
    "Для детей": "детские",
    "Универсальный": "универсальные",
    "Для авто": "для авто",
    "Для дома": "для дома",
}


def trim(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip(" ,.") + "…"


class SeoGenerator:
    def generate_titles(self, data: dict) -> dict[str, str]:
        name = clean_text(data.get("product_name"))
        category = clean_text(data.get("category"))
        audience = clean_text(data.get("target_audience"))
        color = clean_text(data.get("color"))
        complect = clean_text(data.get("size_or_complect"))
        features = csv_items(data.get("key_features"))
        use_cases = clean_text(data.get("use_cases"))

        parts_short = [name]
        if not is_skipped(color) and color.lower() not in name.lower():
            parts_short.append(color.lower())
        if not is_skipped(complect) and complect.lower() not in name.lower():
            parts_short.append(complect.lower())

        audience_word = AUDIENCE_SHORT.get(audience, audience.lower() if audience != SKIPPED else "")
        medium_parts = [audience_word, color.lower() if color != SKIPPED else "", name, category.lower()]
        if complect != SKIPPED:
            medium_parts.append(complect.lower())
        if use_cases != SKIPPED:
            medium_parts.append(use_cases.lower())

        full_parts = [name, color.lower() if color != SKIPPED else "", complect.lower() if complect != SKIPPED else ""]
        full_parts.extend(features[:5])
        if use_cases != SKIPPED:
            full_parts.append(f"для {use_cases.lower()}")

        return {
            "short": trim(", ".join(dict.fromkeys([p for p in parts_short if p and p != SKIPPED])), 60),
            "medium": trim(", ".join(dict.fromkeys([p for p in medium_parts if p and p != SKIPPED])), 120),
            "full": trim(", ".join(dict.fromkeys([p for p in full_parts if p and p != SKIPPED])), 200),
        }

    def generate_quick(self, query: str) -> dict:
        base = clean_text(query)
        words = [word.strip(" ,.;") for word in base.lower().split() if len(word.strip(" ,.;")) > 2]
        unique = list(dict.fromkeys(words))
        titles = [
            trim(base.capitalize(), 60),
            trim(f"{base}, для ежедневного использования", 120),
            trim(f"{base}, практичный вариант для маркетплейса", 120),
            trim(f"{base}, с понятными характеристиками и выгодой", 140),
            trim(f"{base}, карточка товара с SEO-ключами", 140),
        ]
        phrases = [f"{word} купить" for word in unique[:10]] + [f"{word} для маркетплейса" for word in unique[:10]]
        hashtags = [f"#{word.replace('-', '').replace('/', '')}" for word in unique[:20]]
        advantages = [
            "понятная выгода для покупателя",
            "подходит для регулярного использования",
            "удобно сравнивать с аналогами",
            "можно показать ключевые свойства в инфографике",
            "легко адаптировать под разные площадки",
        ]
        return {
            "titles": titles,
            "phrases": phrases[:20],
            "hashtags": hashtags[:20],
            "description": f"{base.capitalize()} — товар, который важно показать через понятные выгоды, характеристики и сценарии применения. В карточке стоит сделать акцент на назначении, комплектации, материале и главном преимуществе.",
            "advantages": advantages,
        }
