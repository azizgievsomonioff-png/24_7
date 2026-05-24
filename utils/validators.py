def has_photo(message) -> bool:
    return bool(getattr(message, "photo", None))
