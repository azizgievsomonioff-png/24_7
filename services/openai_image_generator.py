import asyncio
import base64
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def build_marketplace_image_prompt(base_prompt: str, slide_number: int, marketplace: str, product_name: str) -> str:
    prompt = f"""
Создай вертикальную инфографику для маркетплейса в формате 3:4.
Площадка: {marketplace}.
Товар: {product_name}.
Слайд №{slide_number}.

Используй исходное фото товара как главный объект, если оно передано.
Сохрани форму, цвет, пропорции и внешний вид товара.
Не меняй логотипы, упаковку и важные детали товара.

Требования к дизайну:
- современный маркетплейсный стиль;
- крупный товар как главный объект;
- чистый современный фон;
- крупные читаемые надписи на русском языке;
- не больше 1 заголовка и 2-4 коротких подписей;
- минимум текста;
- аккуратные бейджи и иконки;
- без лишних объектов;
- без чужих брендов и логотипов маркетплейсов;
- без водяных знаков;
- без мелких нечитаемых надписей;
- без медицинских и неподтвержденных обещаний;
- не добавлять значки "сертифицировано", "оригинал", "№1", если это не указано пользователем.

Основной промт:
{base_prompt}
""".strip()
    return prompt[:12000]


class OpenAIImageGenerator:
    def __init__(
        self,
        api_key: str,
        model: str,
        size: str,
        quality: str,
        output_format: str,
        base_url: str = "",
    ):
        self.api_key = api_key
        self.base_url = base_url.strip()
        self.model = model
        self.size = size
        self.quality = quality
        self.output_format = output_format.lower().strip() or "png"

    def _client(self):
        from openai import OpenAI

        if self.base_url:
            return OpenAI(api_key=self.api_key, base_url=self.base_url)
        return OpenAI(api_key=self.api_key)

    async def generate_image_from_prompt(self, prompt: str, output_path: str) -> str:
        def request() -> str:
            client = self._client()
            response = client.images.generate(
                model=self.model,
                prompt=prompt,
                size=self.size,
                quality=self.quality,
                output_format=self.output_format,
            )
            return self._save_response(response, output_path)

        try:
            return await asyncio.to_thread(request)
        except Exception:
            logger.exception("OpenAI image generation failed")
            raise

    async def generate_image_with_reference(self, prompt: str, reference_image_path: str, output_path: str) -> str:
        if not Path(reference_image_path).exists():
            raise FileNotFoundError(f"Reference image not found: {reference_image_path}")

        def request() -> str:
            client = self._client()
            with open(reference_image_path, "rb") as image_file:
                response = client.images.edit(
                    model=self.model,
                    image=image_file,
                    prompt=prompt,
                    size=self.size,
                    quality=self.quality,
                    output_format=self.output_format,
                )
            return self._save_response(response, output_path)

        try:
            return await asyncio.to_thread(request)
        except Exception:
            logger.exception("OpenAI image edit failed")
            raise

    @staticmethod
    def _extract_b64(response) -> str:
        data = getattr(response, "data", None)
        if not data:
            raise ValueError("OpenAI returned empty image data")
        first = data[0]
        image_base64 = getattr(first, "b64_json", None)
        if image_base64 is None and isinstance(first, dict):
            image_base64 = first.get("b64_json")
        if not image_base64:
            image_url = getattr(first, "url", None)
            if image_url is None and isinstance(first, dict):
                image_url = first.get("url")
            if isinstance(image_url, str) and image_url.startswith("data:image/") and ";base64," in image_url:
                image_base64 = image_url.split(";base64,", 1)[1]
        if not image_base64:
            raise ValueError("OpenAI did not return b64_json")
        return image_base64

    def _save_response(self, response, output_path: str) -> str:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        image_base64 = self._extract_b64(response)
        image_bytes = base64.b64decode(image_base64)
        path.write_bytes(image_bytes)
        return str(path)
