from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import joblib
import numpy as np
from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from app.services.evaluation_service import load_evaluation
from app.services.image_service import allowed_file, validate_image
from app.services.predictor import CornDiseasePredictor
from app.utils.image_features import extract_features


evaluation_bp = Blueprint("evaluation", __name__)


def _model_rows(data: dict):
    return data.get("models", []) if data else []


def _similarity(distance: float) -> float:
    # Indeks kemiripan (bukan accuracy): semakin kecil jarak feature vector,
    # semakin besar nilainya. Hanya untuk membaca kedekatan citra baru.
    return float(np.exp(-float(distance) / 10.0) * 100.0)


@evaluation_bp.get("/")
def evaluation():
    data = load_evaluation(current_app.config["MODEL_FOLDER"])
    return jsonify({"success": True, "data": data})


@evaluation_bp.get("/summary")
def summary():
    data = load_evaluation(current_app.config["MODEL_FOLDER"])
    return jsonify({"success": True, "data": data.get("models", []), "best_model": data.get("best_model"), "dataset": data.get("dataset", {})})


@evaluation_bp.get("/c45")
def c45():
    data = load_evaluation(current_app.config["MODEL_FOLDER"])
    rows = [x for x in _model_rows(data) if x.get("model") == "c45"]
    row = rows[0] if rows else None
    if row:
        row = {**row, "classes": data.get("dataset", {}).get("classes", []), "feature_count": data.get("dataset", {}).get("feature_count")}
    return jsonify({"success": True, "data": row})


@evaluation_bp.get("/gaussian-nb")
def gaussian_nb():
    data = load_evaluation(current_app.config["MODEL_FOLDER"])
    rows = [x for x in _model_rows(data) if x.get("model") == "gaussian_nb"]
    row = rows[0] if rows else None
    if row:
        row = {**row, "classes": data.get("dataset", {}).get("classes", []), "feature_count": data.get("dataset", {}).get("feature_count")}
    return jsonify({"success": True, "data": row})


@evaluation_bp.get("/knn")
def knn():
    data = load_evaluation(current_app.config["MODEL_FOLDER"])
    rows = [x for x in _model_rows(data) if x.get("model") == "knn"]
    rows = [
        {**row, "classes": data.get("dataset", {}).get("classes", []), "feature_count": data.get("dataset", {}).get("feature_count")}
        for row in rows
    ]
    return jsonify({"success": True, "data": rows})


@evaluation_bp.post("/image")
def evaluate_image():
    image = request.files.get("image")
    if image is None or image.filename == "":
        return jsonify({"success": False, "message": "Gambar belum dipilih."}), 400
    if not allowed_file(image.filename, current_app.config["ALLOWED_EXTENSIONS"]):
        return jsonify({"success": False, "message": "Format gambar tidak didukung."}), 400

    model_dir = Path(current_app.config["MODEL_FOLDER"])
    required = ["scaler.joblib", "label_encoder.joblib", "c45.joblib", "gaussian_nb.joblib"]
    missing = [x for x in required if not (model_dir / x).exists()]
    if missing:
        return jsonify({"success": False, "message": "Model belum lengkap. Jalankan training terlebih dahulu: python -m app.utils.train_models"}), 400

    upload_dir = Path(current_app.config["DATA_ROOT"]) / "evaluation_inputs"
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}_{secure_filename(image.filename)}"
    image_path = upload_dir / filename
    image.save(image_path)

    try:
        valid, message = validate_image(image_path)
        if not valid:
            image_path.unlink(missing_ok=True)
            return jsonify({"success": False, "message": f"File gambar tidak valid: {message}"}), 400

        features, metadata = extract_features(image_path)

        # Gunakan gate yang sama dengan deteksi utama agar halaman Uji Citra
        # tidak memaksa foto wajah/benda lain menjadi Bulai, Hawar, atau Bercak.
        predictor = CornDiseasePredictor(model_dir)
        gate_ok, gate_message, gate_info = predictor._validate_corn_leaf(image_path, features)
        if not gate_ok:
            image_path.unlink(missing_ok=True)
            return jsonify({
                "success": False,
                "message": gate_message,
                "code": "UNSUPPORTED_IMAGE",
                "validation": gate_info,
            }), 422

        scaler = joblib.load(model_dir / "scaler.joblib")
        encoder = joblib.load(model_dir / "label_encoder.joblib")
        x = scaler.transform([features])

        models = [
            ("c45", joblib.load(model_dir / "c45.joblib"), None),
            ("gaussian_nb", joblib.load(model_dir / "gaussian_nb.joblib"), None),
        ]
        for k in [1, 3, 5, 7, 9]:
            path = model_dir / f"knn_k{k}.joblib"
            if path.exists():
                models.append(("knn", joblib.load(path), k))
        if not any(name == "knn" for name, _, _ in models) and (model_dir / "knn.joblib").exists():
            evaluation = load_evaluation(model_dir)
            k = (evaluation.get("best_model") or {}).get("k")
            models.append(("knn", joblib.load(model_dir / "knn.joblib"), k))

        predictions = []
        for name, model, k in models:
            pred = int(model.predict(x)[0])
            label = str(encoder.inverse_transform([pred])[0])
            proba = model.predict_proba(x)[0].tolist() if hasattr(model, "predict_proba") else []
            confidence = float(max(proba)) if proba else 1.0
            predictions.append({
                "model": name, "k": k, "predicted_class": label,
                "confidence": confidence,
                "probabilities": {str(c): float(v) for c, v in zip(encoder.classes_, proba)},
            })

        ref_path = model_dir / "dataset_reference.npz"
        similarities = {}
        if ref_path.exists():
            ref = np.load(ref_path)
            for split in ("train", "val", "test"):
                arr = ref[split]
                distances = np.linalg.norm(arr - x[0], axis=1)
                nearest = float(distances.min()) if len(distances) else float("nan")
                similarities[split] = {
                    "nearest_distance": nearest,
                    "similarity": _similarity(nearest) if np.isfinite(nearest) else 0.0,
                    "samples": int(len(arr)),
                }

        true_label = request.form.get("true_label") or None
        for row in predictions:
            row["label_match"] = None if not true_label else bool(row["predicted_class"] == true_label)

        return jsonify({
            "success": True,
            "data": {
                "image": "/data/evaluation_inputs/" + filename,
                "feature_count": int(len(features)),
                "entropy": float(metadata["entropy"]),
                "predictions": predictions,
                "similarity": similarities,
                "true_label": true_label,
            },
        })
    except Exception as exc:
        image_path.unlink(missing_ok=True)
        return jsonify({"success": False, "message": f"Pengujian citra gagal: {exc}"}), 500
