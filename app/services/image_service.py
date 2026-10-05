from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from PIL import Image


def allowed_file(filename: str, extensions: set[str]) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in extensions


def make_unique_filename(filename: str) -> str:
    extension = Path(filename).suffix.lower() or ".jpg"
    return f"{uuid4().hex}{extension}"


def validate_image(path: str | Path) -> tuple[bool, str]:
    try:
        with Image.open(path) as image:
            image.verify()
        return True, "valid"
    except Exception as exc:
        return False, str(exc)
