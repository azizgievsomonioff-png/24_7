from html import escape


TELEGRAM_LIMIT = 3900
SKIPPED = "Не указано"


def clean_text(value: str | None) -> str:
    if not value:
        return SKIPPED
    value = " ".join(value.strip().split())
    return value or SKIPPED


def is_skipped(value: str | None) -> bool:
    return clean_text(value) == SKIPPED


def h(value: str | int | None) -> str:
    return escape(str(value or ""))


def chunk_text(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    for part in text.split("\n\n"):
        if len(current) + len(part) + 2 > limit:
            if current:
                chunks.append(current)
            current = part
        else:
            current = f"{current}\n\n{part}" if current else part
    if current:
        chunks.append(current)
    return chunks


def csv_items(value: str | None) -> list[str]:
    if is_skipped(value):
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]
