from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from skimage.measure import shannon_entropy

from app.models.disease_symptom import DiseaseSymptom


def get_symptoms_by_disease() -> dict:
    result: dict[str, list[dict]] = {}
    records = DiseaseSymptom.query.filter_by(is_active=True).order_by(
        DiseaseSymptom.disease_class,
        DiseaseSymptom.id,
    ).all()
    for item in records:
        result.setdefault(item.disease_class, []).append({
            "code": item.symptom_code,
            "name": item.symptom_name,
            "description": item.description,
            "weight": item.weight,
        })
    return result


def score_symptoms(disease_class: str, selected_codes: list[str]) -> float:
    records = DiseaseSymptom.query.filter_by(
        disease_class=disease_class,
        is_active=True,
    ).all()
    total = sum(float(x.weight or 0) for x in records)
    matched = sum(
        float(x.weight or 0)
        for x in records
        if x.symptom_code in selected_codes
    )
    return round((matched / total) * 100, 2) if total else 0.0


def recommended_symptoms(disease_class: str) -> list[dict]:
    return get_symptoms_by_disease().get(disease_class, [])


def _clip_score(value: float, low: float, high: float) -> float:
    if high <= low:
        return 0.0
    return float(np.clip((value - low) / (high - low), 0.0, 1.0) * 100.0)


def _image_metrics(image_path: str | Path) -> dict[str, float]:
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Gambar gejala tidak dapat dibaca: {image_path}")

    image = cv2.resize(image, (224, 224), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Mask warna dibuat sebagai indikator visual, bukan sebagai pengganti model klasifikasi.
    brown = ((h <= 30) & (s >= 55) & (v >= 35) & (v <= 220))
    yellow = ((h >= 18) & (h <= 45) & (s >= 55) & (v >= 90))
    pale_yellow = ((h >= 18) & (h <= 45) & (s >= 25) & (s <= 150) & (v >= 130))
    white_gray = (s <= 55) & (v >= 145)
    dark = (v <= 75) & (s >= 35)
    gray_green = (h >= 30) & (h <= 90) & (s >= 20) & (s <= 125) & (v >= 45) & (v <= 210)

    edges = cv2.Canny(gray, 60, 140)
    edge_density = float((edges > 0).mean())

    def ratio(mask: np.ndarray) -> float:
        return float(mask.mean())

    # Estimasi bentuk lesi dari komponen terhubung pada mask cokelat.
    brown_u8 = (brown.astype(np.uint8) * 255)
    kernel = np.ones((3, 3), np.uint8)
    brown_u8 = cv2.morphologyEx(brown_u8, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(brown_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    elongated = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 35:
            continue
        x, y, w, h_box = cv2.boundingRect(contour)
        short_side = max(min(w, h_box), 1)
        long_side = max(w, h_box)
        aspect = long_side / short_side
        if aspect >= 1.8:
            elongated.append(min(aspect / 5.0, 1.0) * min(area / 1000.0, 1.0))
    elongated_score = float(np.clip(np.mean(elongated) if elongated else 0.0, 0, 1) * 100)

    entropy = float(shannon_entropy(gray))
    return {
        "brown": ratio(brown),
        "yellow": ratio(yellow),
        "pale_yellow": ratio(pale_yellow),
        "white_gray": ratio(white_gray),
        "dark": ratio(dark),
        "gray_green": ratio(gray_green),
        "edge_density": edge_density,
        "elongated": elongated_score,
        "entropy": entropy,
    }


def _disease_evidence(disease_class: str, m: dict[str, float]) -> dict[str, float]:
    """Mengubah indikator visual citra menjadi skor bukti 0-100 per gejala.

    Skor ini adalah *visual symptom evidence*, bukan confidence model klasifikasi.
    Gejala seperti pertumbuhan tanaman terhambat tidak dapat dipastikan dari satu
    foto daun saja; indikator yang digunakan adalah proxy visual yang transparan.
    """
    brown = _clip_score(m["brown"], 0.02, 0.28)
    yellow = _clip_score(m["yellow"], 0.03, 0.35)
    pale = _clip_score(m["pale_yellow"], 0.05, 0.45)
    dark = _clip_score(m["dark"], 0.01, 0.20)
    gray_green = _clip_score(m["gray_green"], 0.05, 0.45)
    edge = _clip_score(m["edge_density"], 0.03, 0.22)
    elongated = m["elongated"]
    coating = _clip_score(m["white_gray"], 0.05, 0.35)
    entropy = _clip_score(m["entropy"], 4.0, 7.8)

    if disease_class == "Bercak_Daun":
        return {
            "BD01": brown,
            "BD02": elongated,
            "BD03": yellow,
            "BD04": float(np.clip(0.55 * brown + 0.25 * dark + 0.20 * edge, 0, 100)),
        }
    if disease_class == "Hawar_Daun":
        return {
            "HD01": float(np.clip(0.60 * elongated + 0.40 * brown, 0, 100)),
            "HD02": gray_green,
            "HD03": float(np.clip(0.60 * dark + 0.40 * entropy, 0, 100)),
            "HD04": float(np.clip(0.50 * brown + 0.30 * edge + 0.20 * entropy, 0, 100)),
        }
    if disease_class == "Bulai_Daun":
        return {
            "BL01": pale,
            "BL02": float(np.clip(0.65 * elongated + 0.35 * yellow, 0, 100)),
            # Tidak dapat dibuktikan dari foto satu daun; gunakan indikator klorosis sebagai proxy.
            "BL03": float(np.clip(0.75 * pale + 0.25 * yellow, 0, 100)),
            "BL04": coating,
        }
    return {}


def analyze_symptoms(image_path: str | Path, disease_class: str) -> dict:
    records = DiseaseSymptom.query.filter_by(
        disease_class=disease_class,
        is_active=True,
    ).order_by(DiseaseSymptom.id).all()
    metrics = _image_metrics(image_path)
    evidence = _disease_evidence(disease_class, metrics)

    details = []
    total_weight = 0.0
    weighted_score = 0.0
    selected_codes = []
    for record in records:
        score = round(float(np.clip(evidence.get(record.symptom_code, 0.0), 0, 100)), 1)
        weight = float(record.weight or 0)
        total_weight += weight
        weighted_score += score * weight
        if score >= 50.0:
            selected_codes.append(record.symptom_code)
        details.append({
            "code": record.symptom_code,
            "name": record.symptom_name,
            "description": record.description,
            "weight": weight,
            "score": score,
            "matched": score >= 50.0,
        })

    overall = round(weighted_score / total_weight, 1) if total_weight else 0.0
    return {
        "overall": overall,
        "selected_codes": selected_codes,
        "details": details,
        "metrics": {k: round(v, 4) for k, v in metrics.items()},
    }
