from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import cv2

from app.utils.image_features import extract_features


CLASS_NAMES = ["Bercak_Daun", "Hawar_Daun", "Bulai_Daun"]


class CornDiseasePredictor:
    def __init__(self, model_dir: str | Path):
        self.model_dir = Path(model_dir)
        self.scaler = joblib.load(self.model_dir / "scaler.joblib")
        self.encoder = joblib.load(self.model_dir / "label_encoder.joblib")
        self.c45 = joblib.load(self.model_dir / "c45.joblib")
        self.gaussian_nb = joblib.load(self.model_dir / "gaussian_nb.joblib")
        self.knn = joblib.load(self.model_dir / "knn.joblib")

        evaluation_path = self.model_dir / "evaluation.json"
        self.evaluation = json.loads(evaluation_path.read_text(encoding="utf-8")) if evaluation_path.exists() else {}

    def _decode(self, values):
        return self.encoder.inverse_transform(values)

    def _validate_corn_leaf(self, image_path: str | Path, features: np.ndarray) -> tuple[bool, str, dict]:
        """Reject obvious non-corn/non-leaf images before closed-set classification.

        The classifier only knows three classes, so without this gate an unrelated
        image can still be forced into one of the three classes. This gate combines
        a simple leaf-colour/vegetation check with distance to the training class
        centroids. It is intentionally conservative for the three supported
        diseases: Bercak Daun, Hawar Daun, and Bulai Daun.
        """
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            return False, "Gambar tidak dapat dibaca.", {}

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        # Corn leaves are predominantly green/yellow-green. Include yellow-green
        # to avoid rejecting Bulai images whose leaves can look pale.
        leaf_mask = (
            (hsv[:, :, 0] >= 18) & (hsv[:, :, 0] <= 100) &
            (hsv[:, :, 1] >= 28) & (hsv[:, :, 2] >= 45)
        )
        leaf_ratio = float(leaf_mask.mean())

        # A second cue: pixels with a green/yellow-green relationship in RGB.
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        green_yellow_ratio = float(((g >= r * 0.90) & (g >= b * 1.05) & (g > 0.20)).mean())

        # Require a meaningful amount of leaf-like pixels.
        leaf_like = leaf_ratio >= 0.18 or green_yellow_ratio >= 0.14
        if not leaf_like:
            return False, (
                "Gambar tidak dikenali sebagai daun jagung. "
                "Gunakan foto daun jagung yang menampilkan permukaan daun dengan jelas."
            ), {"leaf_ratio": leaf_ratio, "green_yellow_ratio": green_yellow_ratio}

        x = self.scaler.transform([features])

        # Compare with reference samples if available. This prevents the closed-set
        # model from confidently forcing very different images into a disease class.
        reference_path = self.model_dir / "dataset_reference.npz"
        if reference_path.exists():
            ref = np.load(reference_path)
            ref_x = np.vstack([ref["train"], ref["val"], ref["test"]])
            ref_y = np.concatenate([ref["train_labels"], ref["val_labels"], ref["test_labels"]])
            ref_x = self.scaler.transform(ref_x)
            centroids = []
            for cls in np.unique(ref_y):
                centroids.append(ref_x[ref_y == cls].mean(axis=0))
            centroid_distance = float(min(np.linalg.norm(x[0] - c) for c in centroids))
            if centroid_distance > 1200.0:
                return False, (
                    "Gambar berada di luar karakteristik data daun jagung yang didukung "
                    "(Bulai, Hawar, dan Bercak). Silakan gunakan gambar daun jagung yang sesuai."
                ), {
                    "leaf_ratio": leaf_ratio,
                    "green_yellow_ratio": green_yellow_ratio,
                    "reference_distance": centroid_distance,
                }
        else:
            centroid_distance = None

        return True, "ok", {
            "leaf_ratio": leaf_ratio,
            "green_yellow_ratio": green_yellow_ratio,
            "reference_distance": centroid_distance,
        }

    def predict(self, image_path: str | Path, model_name: str | None = None) -> dict:
        features, metadata = extract_features(image_path)
        valid, validation_message, validation = self._validate_corn_leaf(image_path, features)
        if not valid:
            raise ValueError(validation_message)
        x = self.scaler.transform([features])

        best = self.evaluation.get("best_model", {})
        selected = model_name or best.get("model", "knn")
        model = {
            "c45": self.c45,
            "gaussian_nb": self.gaussian_nb,
            "knn": self.knn,
        }.get(selected)
        if model is None:
            raise ValueError(f"Model tidak dikenal: {selected}")

        encoded = model.predict(x)
        label = str(self._decode(encoded)[0])
        probabilities = None
        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(x)[0].tolist()

        class_probabilities = {}
        if probabilities is not None:
            for name, probability in zip(self.encoder.classes_, probabilities):
                class_probabilities[str(name)] = float(probability)
            confidence = float(max(probabilities))
        else:
            confidence = 1.0

        # Closed-set models should not make a low-confidence decision for an
        # unsupported image. Keep the threshold moderate so valid disease photos
        # are still accepted.
        if confidence < 0.45:
            raise ValueError(
                "Gambar tidak cukup meyakinkan sebagai salah satu penyakit daun jagung "
                "yang didukung (Bulai, Hawar, atau Bercak). Gunakan foto daun yang lebih jelas."
            )

        return {
            "model": selected,
            "predicted_class": label,
            "confidence": confidence,
            "probabilities": class_probabilities,
            "feature_vector": features.tolist(),
            "feature_names": metadata["feature_names"],
            "feature_count": len(features),
            "entropy": metadata["entropy"],
            "feature_groups": metadata["feature_groups"],
            "input_validation": validation,
        }
