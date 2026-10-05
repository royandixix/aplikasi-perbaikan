"""Memindahkan artefak runtime lama dari app/static ke folder data project.

Jalankan dari folder project (yang berisi run.py/config.py):
    python -m app.utils.migrate_runtime_data
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models.prediction import PredictionHistory
from app.models.processing_step import ProcessingStep


def copy_tree(source: Path, target: Path) -> int:
    if not source.exists():
        return 0
    count = 0
    for item in source.rglob("*"):
        if not item.is_file():
            continue
        rel = item.relative_to(source)
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copy2(item, dest)
        count += 1
    return count


def convert_url(value: str | None, old_root: Path, new_root: Path) -> str | None:
    if not value:
        return value
    raw = str(value).replace("\\", "/")
    if raw.startswith("/data/"):
        return raw
    if raw.startswith("/static/"):
        rel = raw[len("/static/"):]
        if rel.startswith("uploads/"):
            return "/data/uploads/" + rel[len("uploads/"):]
        if rel.startswith("processed/"):
            return "/data/processed/" + rel[len("processed/"):]
        if rel.startswith("heatmaps/"):
            return "/data/heatmaps/" + rel[len("heatmaps/"):]
        return raw

    path = Path(raw)
    try:
        rel = path.resolve().relative_to(old_root.resolve())
        return "/data/" + rel.as_posix()
    except (ValueError, OSError):
        pass
    marker = "/app/static/"
    if marker in raw:
        rel = raw.split(marker, 1)[1]
        if rel.startswith(("uploads/", "processed/", "heatmaps/")):
            return "/data/" + rel
    return value


def main() -> None:
    app = create_app()
    with app.app_context():
        data_root = Path(app.config["DATA_ROOT"])
        static_root = Path(app.static_folder)
        old_root = static_root
        for folder in ("uploads", "processed", "heatmaps"):
            (data_root / folder).mkdir(parents=True, exist_ok=True)
            copied = copy_tree(old_root / folder, data_root / folder)
            print(f"{folder}: {copied} file diperiksa/disalin")

        changed = 0
        for record in PredictionHistory.query.all():
            old_image = record.image_path
            record.image_path = convert_url(record.image_path, old_root, data_root)

            processing = json.loads(record.processing_json or "{}")
            record.processing_json = json.dumps({
                key: convert_url(value, old_root, data_root)
                for key, value in processing.items()
            })

            steps = ProcessingStep.query.filter_by(prediction_id=record.id).all()
            for step in steps:
                step.image_path = convert_url(step.image_path, old_root, data_root)
            if record.image_path != old_image:
                changed += 1

        db.session.commit()
        print(f"Database: {changed} record diperbarui.")
        print(f"Semua artefak runtime sekarang diarahkan ke: {data_root}")


if __name__ == "__main__":
    main()
