from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import ConfusionMatrixDisplay


def save_confusion_heatmap(matrix, labels, output_path: str | Path, title: str) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 5), dpi=140)
    ConfusionMatrixDisplay(
        confusion_matrix=np.asarray(matrix),
        display_labels=labels,
    ).plot(ax=ax, cmap="Blues", values_format="d", colorbar=True)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
