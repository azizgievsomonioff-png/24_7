import json

from database import queries


async def save_project(telegram_id: int, product_data: dict, result: dict) -> int:
    user_id = await queries.get_user_id(telegram_id)
    if user_id is None:
        user_id = await queries.upsert_user(telegram_id, None, None)
    return await queries.create_project(
        user_id=user_id,
        marketplace=product_data.get("marketplace", ""),
        category=product_data.get("category", ""),
        product_name=product_data.get("product_name", ""),
        product_data_json=json.dumps(product_data, ensure_ascii=False),
        main_image_path=product_data.get("main_image_path"),
        result_json=json.dumps(result, ensure_ascii=False),
    )
