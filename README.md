# Marketplace Card Bot

Telegram-бот для MVP-генерации карточек товаров и инфографики для Ozon, Wildberries, Яндекс.Маркет и Avito.

Бот собирает данные о товаре, сохраняет фото, генерирует SEO-названия, описание, характеристики, план инфографики, промты для слайдов, ТЗ для дизайнера, TXT-экспорт и готовые изображения через OpenAI Image API.

## Установка

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Linux/Mac:

```bash
source venv/bin/activate
```

Установите зависимости:

```bash
pip install -r requirements.txt
```

## Настройка .env

Скопируйте `.env.example` в `.env`:

```bash
cp .env.example .env
```

Windows:

```powershell
Copy-Item .env.example .env
```

Заполните переменные:

```env
BOT_TOKEN=PASTE_TELEGRAM_BOT_TOKEN_HERE
ADMIN_ID=
DATABASE_PATH=data/bot.db
OPENAI_API_KEY=PASTE_OPENAI_API_KEY_HERE
OPENAI_BASE_URL=
OPENAI_TEXT_MODEL=gpt-5.5
OPENAI_IMAGE_MODEL=gpt-image-1.5
OPENAI_IMAGE_SIZE=1024x1536
OPENAI_IMAGE_QUALITY=medium
OPENAI_IMAGE_OUTPUT_FORMAT=png
```

`BOT_TOKEN` нужно получить у BotFather. `OPENAI_API_KEY` нужен только для генерации готовых изображений. Если ключ пустой, бот запустится, но при попытке генерации картинок покажет сообщение о настройке ключа.

Если используется OpenAI-compatible провайдер, например AITUNNEL, нужно указать не только ключ, но и endpoint:

```env
OPENAI_API_KEY=sk-aitunnel-...
OPENAI_BASE_URL=https://api.aitunnel.ru/v1/
```

## Запуск

```bash
python bot.py
```

При первом запуске бот создаст SQLite-базу `data/bot.db` и нужные папки для проектов и экспортов. Если база уже существует, бот безопасно добавит колонку `generated_images_json`.

## Как пользоваться

Команды:

- `/start` — главное меню
- `/new` — создать карточку
- `/projects` — мои проекты
- `/help` — помощь
- `/cancel` — отменить текущий сценарий

Основной сценарий:

1. Выберите маркетплейс.
2. Выберите категорию.
3. Загрузите основное фото товара.
4. Ответьте на вопросы о названии, аудитории, преимуществах, материале, цвете, комплектации, сценариях и болях клиента.
5. Подтвердите текстовую генерацию.
6. Получите SEO, описание, характеристики, план инфографики, промты и TXT-экспорт.
7. При необходимости нажмите `🤖 Сгенерировать промты через ChatGPT`.
8. При необходимости нажмите `🎨 Сгенерировать картинки`.

## Генерация промтов через ChatGPT

Кнопка `🤖 Сгенерировать промты через ChatGPT` отправляет данные товара и фото, если оно доступно, в OpenAI Responses API. Модель берётся из переменной:

```env
OPENAI_TEXT_MODEL=gpt-5.5
```

Если выбранный провайдер не поддерживает `gpt-5.5`, укажите доступную текстовую модель в `.env`.

OpenAI должен вернуть строгий JSON:

```json
{
  "seo_title": "",
  "short_description": "",
  "slides": [
    {
      "slide_number": 1,
      "title": "",
      "goal": "",
      "text_on_slide": [],
      "image_prompt": ""
    }
  ]
}
```

Бот показывает SEO-название, короткое описание и каждый из 6 слайдов отдельным сообщением. У каждого слайда есть кнопки:

- `🔁 Переделать этот слайд`
- `✏️ Добавить правку`
- `📋 Скопировать промт`
- `➡️ Следующий`

Если OpenAI вернул невалидный JSON, бот один раз отправит ответ на исправление. Если ошибка повторится, бот покажет понятное сообщение и запишет подробности в консоль.

## Генерация изображений через OpenAI

API-ключ можно создать в личном кабинете OpenAI Platform. Добавьте ключ в `.env`:

```env
OPENAI_API_KEY=ваш_openai_api_key
```

Параметры генерации:

- `OPENAI_IMAGE_MODEL` — модель изображений, по умолчанию `gpt-image-1.5`
- `OPENAI_TEXT_MODEL` — текстовая модель для промтов через Responses API, по умолчанию `gpt-5.5`
- `OPENAI_BASE_URL` — endpoint для OpenAI-compatible провайдеров, например `https://api.aitunnel.ru/v1/`
- `OPENAI_IMAGE_SIZE` — размер, по умолчанию `1024x1536`
- `OPENAI_IMAGE_QUALITY` — качество, по умолчанию `medium`
- `OPENAI_IMAGE_OUTPUT_FORMAT` — формат файла: `png`, `jpeg` или `webp`

Как запустить генерацию:

1. Создайте карточку товара.
2. Получите текстовый результат и промты.
3. Нажмите `🎨 Сгенерировать картинки`.
4. Подтвердите запуск, потому что генерация может расходовать платный OpenAI API.
5. Бот сгенерирует до 6 слайдов и отправит изображения в Telegram.
6. Нажмите `📦 Скачать картинки ZIP`, чтобы получить архив.

Генерация изображений может быть платной. Стоимость зависит от модели, качества и количества слайдов.

Где сохраняются файлы:

- исходное фото: `data/projects/{telegram_id}/{temp_id}/main.jpg`
- готовые изображения: `data/projects/{telegram_id}/{project_id}/generated/slide_1.png`
- ZIP-архив: `data/exports/images_{telegram_id}_{project_id}.zip`

Если исходное фото не найдено, бот предупредит пользователя и сможет сгенерировать изображения только по описанию. В таком режиме товар может отличаться от реального.

## Структура проекта

```text
marketplace_card_bot/
├── bot.py
├── config.py
├── requirements.txt
├── .env.example
├── README.md
├── handlers/
│   ├── start.py
│   ├── create_card.py
│   ├── projects.py
│   ├── seo.py
│   ├── export.py
│   ├── chatgpt_prompts.py
│   ├── image_generation.py
│   ├── fallback.py
│   └── help.py
├── keyboards/
│   ├── main_menu.py
│   ├── marketplace.py
│   ├── categories.py
│   ├── gender.py
│   ├── result_actions.py
│   ├── chatgpt_prompts.py
│   ├── image_actions.py
│   └── skip.py
├── states/
│   └── card_states.py
├── services/
│   ├── ai_generator.py
│   ├── seo_generator.py
│   ├── infographic_generator.py
│   ├── prompt_generator.py
│   ├── openai_prompt_service.py
│   ├── openai_image_generator.py
│   ├── zip_exporter.py
│   ├── project_storage.py
│   ├── txt_exporter.py
│   ├── background_remover.py
│   └── file_service.py
├── database/
│   ├── db.py
│   ├── models.py
│   └── queries.py
├── data/
│   ├── projects/
│   └── exports/
└── utils/
```

## Что реализовано

- aiogram 3.x, routers, FSM.
- Главное меню с reply-кнопками.
- Inline-кнопки для выбора маркетплейса, категории, аудитории и действий.
- SQLite через aiosqlite.
- Автоматическое сохранение пользователей и проектов.
- Последние 10 проектов пользователя.
- Открытие, удаление и TXT-экспорт проекта.
- Локальная генерация SEO, описания, характеристик, структуры инфографики, промтов и ТЗ.
- Генерация качественных промтов через OpenAI Responses API.
- Переделка и правка отдельного слайда через ChatGPT.
- Генерация готовых изображений через OpenAI Image API.
- Защита от двух одновременных генераций одним пользователем.
- ZIP-архив с готовыми изображениями.
- Быстрый сценарий SEO без фото.
- Быстрый сценарий промтов для инфографики без фото.
- Заготовка `background_remover.py` для будущего API удаления фона.

## Чек-лист проверки

1. Запустить бота.
2. Создать карточку.
3. Загрузить фото.
4. Получить SEO и промты.
5. Нажать `🎨 Сгенерировать картинки`.
6. Подтвердить генерацию.
7. Проверить, что бот отправил 4 картинки или больше, если план содержит дополнительные слайды.
8. Проверить, что файлы появились в `data/projects`.
9. Нажать `📦 Скачать картинки ZIP`.
10. Проверить, что ZIP открывается.

## Что можно добавить позже

- Генерацию разных форматов: `1536x1024`, квадрат, баннеры.
- Предпросмотр и выбор слайдов перед генерацией.
- Удаление фона и подготовку фото товара.
- Админ-панель и лимиты на генерации.
- Оплату и тарифы.
- Более точные шаблоны под категории маркетплейсов.
