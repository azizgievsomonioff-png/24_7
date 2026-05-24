from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    bot_token: str = ""
    admin_id: int | None = None
    database_path: str = "data/bot.db"
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_text_model: str = "gpt-5.5"
    openai_image_model: str = "gpt-image-1.5"
    openai_image_size: str = "1024x1536"
    openai_image_quality: str = "medium"
    openai_image_output_format: str = "png"

    @field_validator("admin_id", mode="before")
    @classmethod
    def empty_admin_id_to_none(cls, value: object) -> object:
        if value == "":
            return None
        return value

    @field_validator("openai_base_url", mode="before")
    @classmethod
    def clean_openai_base_url(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def db_path(self) -> Path:
        path = Path(self.database_path)
        return path if path.is_absolute() else BASE_DIR / path


settings = Settings()  # type: ignore[call-arg]
