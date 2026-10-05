from __future__ import annotations

import json
from pathlib import Path

from flask import Blueprint, current_app, jsonify

from app.extensions import db
from app.models.prediction import PredictionHistory
from app.models.processing_step import ProcessingStep


history_bp = Blueprint("history", __name__)


def file_url(value: str | None) -> str | None:
    """Normalisasi path lama/baru menjadi URL relatif tanpa membocorkan path Windows."""
    if not value:
        return value
    raw = str(value).replace("\\", "/")
    if raw.startswith("/data/") or raw.startswith("/static/"):
        return raw

    data_root = Path(current_app.config["DATA_ROOT"]).resolve()
    static_root = Path(current_app.static_folder).resolve()
    try:
        return "/data/" + Path(raw).resolve().relative_to(data_root).as_posix()
    except (ValueError, OSError):
        pass
    try:
        return "/static/" + Path(raw).resolve().relative_to(static_root).as_posix()
    except (ValueError, OSError):
        pass

    # Dukungan record lama yang tersimpan sebagai C:/.../app/static/...
    marker = "/app/static/"
    if marker in raw:
        return "/static/" + raw.split(marker, 1)[1]
    marker_data = "/data/"
    if marker_data in raw:
        return "/data/" + raw.split(marker_data, 1)[1]
    return ""


def normalize_processing(data: dict) -> dict:
    data = data or {}
    # Format baru: {"files": {...}, "timings": {...}}.
    if "files" in data:
        return {
            "files": {key: file_url(value) for key, value in (data.get("files") or {}).items()},
            "timings": data.get("timings") or {},
        }
    # Format lama tetap didukung agar riwayat sebelumnya tidak rusak.
    return {key: file_url(value) for key, value in data.items()}



def build_feature_groups(feature_data: dict) -> dict:
    """Pastikan halaman Processing selalu memiliki daftar nilai fitur per metode.

    Record lama pada database hanya menyimpan ``names`` + ``values`` tanpa
    ``groups``. Fungsi ini membangun kembali kelompok fitur dari urutan
    feature vector 173 dimensi agar riwayat lama tetap dapat menampilkan
    nilai RGB/HSV/Histogram/LBP/Entropy/Sobel/Laplacian.
    """
    if not isinstance(feature_data, dict):
        return {}

    existing = feature_data.get("groups") or feature_data.get("feature_groups")
    if isinstance(existing, dict) and existing:
        return existing

    values = feature_data.get("values") or feature_data.get("feature_vector") or []
    names = feature_data.get("names") or feature_data.get("feature_names") or []
    values = [float(v) for v in values]

    # Nama kanonik dipakai untuk record lama yang masih menggunakan
    # rgb_001, hsv_001, dst. Record baru tetap memakai nama dari extractor.
    groups_spec = [
        ("rgb", 12),
        ("hsv", 12),
        ("rgb_hist", 48),
        ("hsv_hist", 48),
        ("gray_hist", 16),
        ("lbp", 26),
        ("entropy", 1),
        ("sobel", 7),
        ("laplacian", 3),
    ]

    def canonical_names(key: str, count: int) -> list[str]:
        if key in {"rgb", "hsv"}:
            channels = ("R", "G", "B") if key == "rgb" else ("H", "S", "V")
            return [f"{key}_{channel}_{stat}" for channel in channels for stat in ("mean", "std", "min", "max")]
        if key in {"rgb_hist", "hsv_hist"}:
            prefix = key
            channels = ("R", "G", "B") if key == "rgb_hist" else ("H", "S", "V")
            return [f"{prefix}_{channel}_bin_{i:02d}" for channel in channels for i in range(1, 17)]
        if key == "gray_hist":
            return [f"gray_hist_C1_bin_{i:02d}" for i in range(1, 17)]
        if key == "lbp":
            return [f"lbp_LBP_bin_{i:02d}" for i in range(1, 27)]
        if key == "entropy":
            return ["entropy"]
        if key == "sobel":
            return ["sobel_x_mean_abs", "sobel_x_std", "sobel_y_mean_abs", "sobel_y_std", "sobel_magnitude_mean", "sobel_magnitude_std", "sobel_magnitude_max"]
        if key == "laplacian":
            return ["laplacian_mean_abs", "laplacian_std", "laplacian_max_abs"]
        return [f"{key}_{i:03d}" for i in range(1, count + 1)]

    groups = {}
    offset = 0
    for key, count in groups_spec:
        chunk = values[offset:offset + count]
        if not chunk:
            break
        source_names = names[offset:offset + len(chunk)]
        # Jika nama lama generik atau jumlah nama tidak cocok, gunakan nama
        # kanonik yang menjelaskan arti setiap nilai.
        import re
        generic_pattern = re.compile(r"^(?:rgb|hsv|rgb_hist|hsv_hist|gray_hist|lbp)_\d+$")
        generic = len(source_names) != len(chunk) or all(generic_pattern.fullmatch(str(n)) for n in source_names)
        use_names = canonical_names(key, len(chunk)) if generic else source_names
        if len(use_names) != len(chunk):
            use_names = canonical_names(key, len(chunk))
        groups[key] = {
            "count": len(chunk),
            "start_index": offset,
            "end_index": offset + len(chunk) - 1,
            "names": use_names,
            "values": chunk,
        }
        offset += count

    return groups

def serialize(record: PredictionHistory) -> dict:
    scores = json.loads(record.symptom_scores_json or "{}")
    feature_data = json.loads(record.feature_vector_json or "{}")
    feature_data["groups"] = build_feature_groups(feature_data)
    feature_data.setdefault("feature_count", len(feature_data.get("values") or feature_data.get("feature_vector") or []))

    return {
        "id": record.id,
        "image_name": record.image_name,
        "image_path": file_url(record.image_path),
        "predicted_class": record.predicted_class,
        "confidence": record.confidence,
        "selected_model": record.selected_model,
        "symptoms": json.loads(record.symptoms_json or "[]"),
        "symptom_scores": scores,
        "symptom_details": scores.get("details", []),
        "symptom_score": scores.get("overall", scores.get(record.predicted_class, 0)),
        "all_predictions": json.loads(record.all_predictions_json or "{}"),
        "processing": normalize_processing(json.loads(record.processing_json or "{}")),
        "feature_vector": feature_data,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


@history_bp.get("/")
def list_history():
    records = PredictionHistory.query.order_by(PredictionHistory.created_at.desc()).all()
    return jsonify({"success": True, "data": [serialize(x) for x in records]})


@history_bp.get("/<int:record_id>")
def detail(record_id: int):
    record = PredictionHistory.query.get_or_404(record_id)
    steps = ProcessingStep.query.filter_by(prediction_id=record.id).order_by(ProcessingStep.step_order).all()
    data = serialize(record)
    data["steps"] = [
        {
            "id": step.id,
            "step_name": step.step_name,
            "description": step.description,
            "image_path": file_url(step.image_path),
            "statistics": json.loads(step.statistics_json or "{}"),
            "step_order": step.step_order,
        }
        for step in steps
    ]
    entropy_step = next((x for x in data["steps"] if x["step_name"].lower() == "entropy"), None)
    if entropy_step:
        stats = entropy_step.get("statistics") or {}
        data["feature_vector"]["entropy"] = stats.get("entropy")
        data["feature_vector"].setdefault("feature_count", stats.get("feature_count"))
    return jsonify({"success": True, "data": data})


@history_bp.delete("/<int:record_id>")
def delete(record_id: int):
    record = PredictionHistory.query.get_or_404(record_id)
    ProcessingStep.query.filter_by(prediction_id=record.id).delete()
    db.session.delete(record)
    db.session.commit()
    return jsonify({"success": True, "message": "Riwayat berhasil dihapus."})
