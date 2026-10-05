from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import cv2
import numpy as np
from time import perf_counter
from skimage.feature import local_binary_pattern
from skimage.measure import shannon_entropy


IMAGE_SIZE: Tuple[int, int] = (224, 224)
LBP_POINTS = 24
LBP_RADIUS = 3
LBP_BINS = LBP_POINTS + 2
HIST_BINS = 16


def read_image(image_path: str | Path) -> np.ndarray:
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Gambar tidak dapat dibaca: {image_path}")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def resize_image(image: np.ndarray) -> np.ndarray:
    return cv2.resize(image, IMAGE_SIZE, interpolation=cv2.INTER_AREA)


def normalize_image(image: np.ndarray) -> np.ndarray:
    return image.astype(np.float32) / 255.0


def _channel_stats(image: np.ndarray, labels: tuple[str, ...] | None = None) -> tuple[list[float], list[str]]:
    values: list[float] = []
    names: list[str] = []
    if labels is None:
        labels = ("R", "G", "B") if image.shape[2] == 3 else tuple(f"C{i+1}" for i in range(image.shape[2]))
    for i, label in enumerate(labels):
        channel = image[..., i].astype(np.float32)
        stats = {
            "mean": float(channel.mean()),
            "std": float(channel.std()),
            "min": float(channel.min()),
            "max": float(channel.max()),
        }
        for stat_name, value in stats.items():
            names.append(f"{label}_{stat_name}")
            values.append(value)
    return values, names


def _histograms(
    image: np.ndarray,
    channel_ranges: tuple[tuple[float, float], ...],
) -> tuple[list[float], list[str]]:
    values: list[float] = []
    names: list[str] = []
    labels = ("R", "G", "B") if image.shape[2] == 3 else tuple(f"C{i+1}" for i in range(image.shape[2]))
    for i, label in enumerate(labels):
        hist, _ = np.histogram(
            image[..., i], bins=HIST_BINS, range=channel_ranges[i]
        )
        hist = hist.astype(np.float32)
        hist /= max(hist.sum(), 1.0)
        for bin_index, value in enumerate(hist.tolist(), start=1):
            names.append(f"{label}_bin_{bin_index:02d}")
            values.append(float(value))
    return values, names


def _lbp_features(gray: np.ndarray) -> tuple[np.ndarray, list[float], list[str]]:
    lbp = local_binary_pattern(
        gray,
        P=LBP_POINTS,
        R=LBP_RADIUS,
        method="uniform",
    )
    hist, _ = np.histogram(
        lbp.ravel(), bins=np.arange(0, LBP_BINS + 1), range=(0, LBP_BINS)
    )
    hist = hist.astype(np.float32)
    hist /= max(hist.sum(), 1.0)
    names = [f"LBP_bin_{i:02d}" for i in range(1, LBP_BINS + 1)]
    return lbp, hist.tolist(), names


def extract_features(image_path: str | Path) -> tuple[np.ndarray, dict]:
    total_start = perf_counter()
    timings: dict[str, float] = {}

    t0 = perf_counter()
    original = read_image(image_path)
    timings["original"] = perf_counter() - t0

    t0 = perf_counter()
    resized = resize_image(original)
    timings["resize"] = perf_counter() - t0

    t0 = perf_counter()
    normalized = normalize_image(resized)
    timings["normalisasi"] = perf_counter() - t0

    t0 = perf_counter()
    hsv = cv2.cvtColor(normalized, cv2.COLOR_RGB2HSV)
    timings["hsv"] = perf_counter() - t0

    t0 = perf_counter()
    gray = cv2.cvtColor(normalized, cv2.COLOR_RGB2GRAY)
    timings["grayscale"] = perf_counter() - t0

    t0 = perf_counter()
    gray_u8 = np.clip(gray * 255.0, 0, 255).astype(np.uint8)
    lbp_image, lbp_hist, lbp_names = _lbp_features(gray_u8)
    timings["lbp"] = perf_counter() - t0

    t0 = perf_counter()
    sobel_x = cv2.Sobel(gray_u8, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray_u8, cv2.CV_32F, 0, 1, ksize=3)
    sobel_magnitude = cv2.magnitude(sobel_x, sobel_y)
    timings["sobel"] = perf_counter() - t0

    t0 = perf_counter()
    laplacian = cv2.Laplacian(gray_u8, cv2.CV_32F)
    timings["laplacian"] = perf_counter() - t0

    features: list[float] = []
    feature_names: list[str] = []
    feature_groups: dict[str, dict] = {}

    def add_group(prefix: str, values: list[float], names: list[str] | None = None) -> None:
        if names is None:
            names = [f"{prefix}_{i+1:03d}" for i in range(len(values))]
        if len(values) != len(names):
            raise ValueError(f"Jumlah nama fitur dan nilai tidak sama untuk {prefix}")
        start = len(features)
        features.extend(values)
        feature_names.extend(names)
        feature_groups[prefix] = {
            "count": len(values),
            "start_index": start,
            "end_index": len(features) - 1,
            "names": names,
            "values": [float(v) for v in values],
        }

    t0 = perf_counter()
    rgb_values, rgb_names = _channel_stats(normalized)
    add_group("rgb", rgb_values, [f"rgb_{n}" for n in rgb_names])
    timings["rgb"] = perf_counter() - t0

    t0 = perf_counter()
    # OpenCV float HSV: H berada pada 0..360, S dan V pada 0..1.
    hsv_values, hsv_names = _channel_stats(hsv, ("H", "S", "V"))
    add_group("hsv", hsv_values, [f"hsv_{n}" for n in hsv_names])
    timings["hsv_stats"] = perf_counter() - t0

    t0 = perf_counter()
    rgb_hist, rgb_hist_names = _histograms(normalized, ((0, 1), (0, 1), (0, 1)))
    hsv_hist, hsv_hist_names = _histograms(hsv, ((0, 360), (0, 1), (0, 1)))
    gray_hist, gray_hist_names = _histograms(gray[..., None], ((0, 1),))
    add_group("rgb_hist", rgb_hist, [f"rgb_hist_{n}" for n in rgb_hist_names])
    add_group("hsv_hist", hsv_hist, [f"hsv_hist_{n}" for n in hsv_hist_names])
    add_group("gray_hist", gray_hist, [f"gray_hist_{n}" for n in gray_hist_names])
    timings["histogram"] = perf_counter() - t0

    t0 = perf_counter()
    # LBP histogram sekarang benar-benar dimasukkan ke feature vector.
    add_group("lbp", lbp_hist, [f"lbp_{n}" for n in lbp_names])
    timings["lbp_feature"] = perf_counter() - t0

    t0 = perf_counter()
    gray_entropy = float(shannon_entropy(gray_u8))
    add_group("entropy", [gray_entropy], ["entropy"])
    timings["entropy"] = perf_counter() - t0

    t0 = perf_counter()
    sobel_values = [
        float(np.mean(np.abs(sobel_x))),
        float(np.std(sobel_x)),
        float(np.mean(np.abs(sobel_y))),
        float(np.std(sobel_y)),
        float(np.mean(sobel_magnitude)),
        float(np.std(sobel_magnitude)),
        float(np.max(sobel_magnitude)),
    ]
    sobel_names = [
        "sobel_x_mean_abs", "sobel_x_std", "sobel_y_mean_abs", "sobel_y_std",
        "sobel_magnitude_mean", "sobel_magnitude_std", "sobel_magnitude_max",
    ]
    add_group("sobel", sobel_values, sobel_names)

    laplacian_values = [
        float(np.mean(np.abs(laplacian))),
        float(np.std(laplacian)),
        float(np.max(np.abs(laplacian))),
    ]
    laplacian_names = ["laplacian_mean_abs", "laplacian_std", "laplacian_max_abs"]
    add_group("laplacian", laplacian_values, laplacian_names)
    timings["feature_vector"] = perf_counter() - t0

    timings["rgb"] = max(timings["rgb"], 0.0)
    timings["hsv"] = max(timings["hsv"], timings.pop("hsv_stats"))
    timings["lbp"] = timings["lbp"] + timings.pop("lbp_feature")
    timings["total"] = perf_counter() - total_start

    metadata: Dict = {
        "original": original,
        "resized": resized,
        "normalized": normalized,
        "rgb": normalized,
        "hsv": hsv,
        "grayscale": gray,
        "lbp": lbp_image,
        "lbp_hist": lbp_hist,
        "sobel_x": sobel_x,
        "sobel_y": sobel_y,
        "sobel_magnitude": sobel_magnitude,
        "laplacian": laplacian,
        "entropy": gray_entropy,
        "feature_names": feature_names,
        "feature_vector": features,
        "feature_groups": feature_groups,
        "timings": timings,
    }

    return np.asarray(features, dtype=np.float32), metadata
