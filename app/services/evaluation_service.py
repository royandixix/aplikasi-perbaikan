from __future__ import annotations

import json
from pathlib import Path


def load_evaluation(model_dir: str | Path) -> dict:
    path = Path(model_dir) / "evaluation.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def best_model(model_dir: str | Path) -> dict:
    return load_evaluation(model_dir).get("best_model", {})
