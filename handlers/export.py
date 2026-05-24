import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile

from services.txt_exporter import export_project_to_txt

router = Router()


@router.callback_query(F.data.startswith("export:"))
async def export_project(callback: CallbackQuery) -> None:
    try:
        project_id = int(callback.data.split(":", 1)[1])
        path = await export_project_to_txt(project_id, callback.from_user.id)
        if not path or not path.exists():
            await callback.message.answer("Файл экспорта не создан. Попробуйте еще раз.")
            return
        await callback.message.answer_document(FSInputFile(path), caption="TXT-файл с результатом готов.")
    except Exception:
        logging.exception("Export failed")
        await callback.message.answer("Произошла ошибка. Попробуйте ещё раз или вернитесь в главное меню.")
    finally:
        await callback.answer()
