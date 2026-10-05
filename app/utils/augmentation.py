from __future__ import annotations

from pathlib import Path

import cv2


def augment_image(image_path: str | Path, output_dir: str | Path) -> list[str]:
    image_path = Path(image_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Gambar tidak dapat dibaca: {image_path}")

    stem = image_path.stem
    outputs = []

    variants = {
        "flip": cv2.flip(image, 1),
        "bright": cv2.convertScaleAbs(image, alpha=1.05, beta=10),
        "dark": cv2.convertScaleAbs(image, alpha=0.90, beta=-5),
    }

    for suffix, result in variants.items():
        target = output_dir / f"aug_{suffix}_{stem}.jpg"
        cv2.imwrite(str(target), result)
        outputs.append(str(target))

    return outputs
