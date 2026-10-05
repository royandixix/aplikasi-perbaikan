from __future__ import annotations

import re
import shutil
from collections import defaultdict
from pathlib import Path

from sklearn.model_selection import train_test_split


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}
SPLITS = {"train": 0.70, "val": 0.15, "test": 0.15}


def _group_key(filename: str) -> str:
    stem = Path(filename).stem
    return re.sub(r"^(aug_tambah_|aug_)", "", stem, flags=re.IGNORECASE)


def split_dataset(raw_dir: str | Path, output_dir: str | Path, seed: int = 42) -> dict:
    raw_dir = Path(raw_dir)
    output_dir = Path(output_dir)

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = {"seed": seed, "splits": defaultdict(lambda: defaultdict(int))}

    for class_dir in sorted(p for p in raw_dir.iterdir() if p.is_dir()):
        files = sorted(
            p for p in class_dir.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        )
        if not files:
            continue

        groups: dict[str, list[Path]] = defaultdict(list)
        for path in files:
            groups[_group_key(path.name)].append(path)

        group_names = sorted(groups)
        train_groups, temp_groups = train_test_split(
            group_names,
            test_size=0.30,
            random_state=seed,
        )
        val_groups, test_groups = train_test_split(
            temp_groups,
            test_size=0.50,
            random_state=seed,
        )

        assignments = {
            "train": set(train_groups),
            "val": set(val_groups),
            "test": set(test_groups),
        }

        for split_name, selected in assignments.items():
            target = output_dir / split_name / class_dir.name
            target.mkdir(parents=True, exist_ok=True)
            for group in selected:
                for source in groups[group]:
                    shutil.copy2(source, target / source.name)
                    summary["splits"][split_name][class_dir.name] += 1

    return {
        "seed": seed,
        "splits": {
            split: dict(classes)
            for split, classes in summary["splits"].items()
        },
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    result = split_dataset(root / "dataset" / "raw", root / "dataset" / "split")
    print(result)
