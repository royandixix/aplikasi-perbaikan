from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from app.utils.image_features import extract_features


def _save_rgb(path: Path, image: np.ndarray) -> None:
    image = np.asarray(image)
    if image.dtype != np.uint8:
        image = np.clip(image * 255 if image.max() <= 1.0 else image, 0, 255).astype(np.uint8)
    cv2.imwrite(str(path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))


def _save_gray(path: Path, image: np.ndarray) -> None:
    image = np.asarray(image)
    image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    cv2.imwrite(str(path), image)


def _save_heat(path: Path, image: np.ndarray, cmap: str = "viridis") -> None:
    plt.figure(figsize=(5, 4), dpi=120)
    plt.imshow(image, cmap=cmap)
    plt.axis("off")
    plt.tight_layout(pad=0)
    plt.savefig(path, bbox_inches="tight", pad_inches=0)
    plt.close()


def _save_histogram(path: Path, image: np.ndarray) -> None:
    plt.figure(figsize=(6, 4), dpi=120)
    if image.ndim == 2:
        plt.hist(image.ravel(), bins=32, range=(0, 255), density=True)
    else:
        for i, name in enumerate(("R", "G", "B")):
            plt.hist(image[..., i].ravel(), bins=32, range=(0, 255), density=True, alpha=0.45, label=name)
        plt.legend()
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight")
    plt.close()


def build_processing_artifacts(image_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    _, data = extract_features(image_path)

    files: dict[str, str] = {}

    mapping = {
        "original": (data["original"], "rgb"),
        "resize": (data["resized"], "rgb"),
        "normalisasi": (data["normalized"], "rgb"),
        "rgb": (data["rgb"], "rgb"),
        "grayscale": (data["grayscale"], "gray"),
        "lbp": (data["lbp"], "heat"),
        "sobel": (data["sobel_magnitude"], "heat"),
        "laplacian": (data["laplacian"], "heat"),
    }

    for name, (image, kind) in mapping.items():
        target = output / f"{name}.png"
        if kind == "rgb":
            _save_rgb(target, image)
        elif kind == "gray":
            _save_gray(target, image)
        else:
            _save_heat(target, image, cmap="magma" if name == "laplacian" else "viridis")
        files[name] = str(target)

    hsv_target = output / "hsv.png"
    hsv_rgb = cv2.cvtColor(data["hsv"].astype("float32"), cv2.COLOR_HSV2RGB)
    _save_rgb(hsv_target, hsv_rgb)
    files["hsv"] = str(hsv_target)

    hist_target = output / "histogram.png"
    _save_histogram(hist_target, data["rgb"])
    files["histogram"] = str(hist_target)

    vector_path = output / "feature_vector.json"
    vector_path.write_text(
        __import__("json").dumps(
            {
                "feature_names": data["feature_names"],
                "feature_vector": data["feature_vector"],
                "feature_count": len(data["feature_vector"]),
                "entropy": data["entropy"],
                "feature_groups": data["feature_groups"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    files["feature_vector"] = str(vector_path)

    return {
        "files": files,
        "feature_names": data["feature_names"],
        "feature_vector": data["feature_vector"],
        "feature_count": len(data["feature_vector"]),
        "entropy": data["entropy"],
        "feature_groups": data["feature_groups"],
        "timings": data.get("timings", {}),
    }
