from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def create_images_zip(image_paths: list[str], output_zip_path: str) -> str:
    zip_path = Path(output_zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        for index, image_path in enumerate(image_paths, start=1):
            path = Path(image_path)
            if path.exists():
                archive.write(path, arcname=f"slide_{index}{path.suffix}")
    return str(zip_path)
