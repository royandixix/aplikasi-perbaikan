from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.prediction import PredictionHistory
from app.models.processing_step import ProcessingStep
from app.services.feature_service import build_processing_artifacts
from app.services.image_service import allowed_file, validate_image
from app.services.predictor import CornDiseasePredictor
from app.services.symptom_service import analyze_symptoms


prediction_bp = Blueprint("prediction", __name__)


def _file_url(path: str | Path) -> str:
    """Converte path físico do project para URL web sem expor C:/Users/..."""
    path = Path(path).resolve()
    data_root = Path(current_app.config["DATA_ROOT"]).resolve()
    static_root = Path(current_app.static_folder).resolve()
    try:
        return "/data/" + path.relative_to(data_root).as_posix()
    except ValueError:
        pass
    try:
        return "/static/" + path.relative_to(static_root).as_posix()
    except ValueError:
        return ""


@prediction_bp.post("/")
def predict():
    image = request.files.get("image")
    if image is None or image.filename == "":
        return jsonify({"success": False, "message": "Gambar belum dipilih."}), 400

    if not allowed_file(image.filename, current_app.config["ALLOWED_EXTENSIONS"]):
        return jsonify({"success": False, "message": "Format gambar tidak didukung."}), 400

    filename = f"{uuid4().hex}_{secure_filename(image.filename)}"
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    image_path = upload_dir / filename
    image.save(image_path)

    valid, message = validate_image(image_path)
    if not valid:
        image_path.unlink(missing_ok=True)
        return jsonify({"success": False, "message": f"File gambar tidak valid: {message}"}), 400

    processing_dir = Path(current_app.config["PROCESSED_FOLDER"]) / image_path.stem
    processing = build_processing_artifacts(image_path, processing_dir)

    predictor = CornDiseasePredictor(current_app.config["MODEL_FOLDER"])
    model_name = request.form.get("model") or None
    try:
        prediction = predictor.predict(image_path, model_name=model_name)
    except ValueError as exc:
        # Jangan simpan gambar yang ditolak sebagai riwayat deteksi.
        image_path.unlink(missing_ok=True)
        return jsonify({
            "success": False,
            "message": str(exc),
            "code": "UNSUPPORTED_IMAGE",
        }), 422

    # Gejala dihitung otomatis dari bukti visual citra.
    # Form upload/kamera tidak perlu mengirim checkbox symptoms.
    symptom_analysis = analyze_symptoms(image_path, prediction["predicted_class"])
    selected_codes = symptom_analysis["selected_codes"]
    symptom_score = symptom_analysis["overall"]
    symptoms = symptom_analysis["details"]

    record = PredictionHistory(
        image_name=secure_filename(image.filename),
        image_path=_file_url(image_path),
        predicted_class=prediction["predicted_class"],
        confidence=prediction["confidence"],
        selected_model=prediction["model"],
        symptoms_json=json.dumps(selected_codes),
        symptom_scores_json=json.dumps({
            "overall": symptom_score,
            "details": symptom_analysis["details"],
            "metrics": symptom_analysis["metrics"],
        }),
        all_predictions_json=json.dumps(prediction["probabilities"]),
        processing_json=json.dumps({
            "files": {
                key: _file_url(value)
                for key, value in processing["files"].items()
            },
            "timings": processing.get("timings", {}),
        }),
        feature_vector_json=json.dumps({
            "names": prediction["feature_names"],
            "values": prediction["feature_vector"],
            "entropy": prediction["entropy"],
            "groups": prediction.get("feature_groups", {}),
        }),
    )
    db.session.add(record)
    db.session.flush()

    processing_order = [
        ("Original", "Citra asli sebelum pemrosesan", "original"),
        ("Resize", "Citra diubah ke ukuran 224x224", "resize"),
        ("Normalisasi", "Nilai piksel dinormalisasi ke rentang 0-1", "normalisasi"),
        ("RGB", "Representasi ruang warna RGB", "rgb"),
        ("HSV", "Representasi ruang warna HSV", "hsv"),
        ("Grayscale", "Konversi citra menjadi skala keabuan", "grayscale"),
        ("Histogram", "Distribusi intensitas/warna", "histogram"),
        ("LBP", "Ekstraksi tekstur Local Binary Pattern", "lbp"),
        ("Entropy", f"Nilai entropy: {processing['entropy']:.4f}", None),
        ("Sobel", "Ekstraksi tepi menggunakan Sobel", "sobel"),
        ("Laplacian", "Ekstraksi perubahan intensitas menggunakan Laplacian", "laplacian"),
        ("Feature Vector", f"Jumlah fitur: {processing['feature_count']}", "feature_vector"),
    ]

    for order, (name, description, key) in enumerate(processing_order, start=1):
        step = ProcessingStep(
            prediction_id=record.id,
            step_name=name,
            description=description,
            image_path=_file_url(processing["files"][key]) if key and key != "feature_vector" else None,
            statistics_json=json.dumps({
                "feature_count": processing["feature_count"],
                "entropy": processing["entropy"],
                "time": processing.get("timings", {}).get(key or "entropy"),
            }) if key in {"feature_vector", None} or key in processing.get("timings", {}) else None,
            step_order=order,
        )
        db.session.add(step)

    db.session.commit()

    return jsonify({
        "success": True,
        "data": {
            "id": record.id,
            "image": record.image_path,
            "predicted_class": prediction["predicted_class"],
            "confidence": prediction["confidence"],
            "model": prediction["model"],
            "probabilities": prediction["probabilities"],
            "symptoms": symptoms,
            "selected_symptoms": selected_codes,
            "symptom_score": symptom_score,
            "processing": {
                key: _file_url(value)
                for key, value in processing["files"].items()
            },
            "feature_count": prediction["feature_count"],
            "feature_vector": prediction["feature_vector"],
            "feature_names": prediction["feature_names"],
            "feature_groups": prediction.get("feature_groups", {}),
            "timings": processing.get("timings", {}),
            "symptom_details": symptom_analysis["details"],
            "symptom_metrics": symptom_analysis["metrics"],
        },
    })
