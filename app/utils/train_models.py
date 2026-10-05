from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_recall_fscore_support
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text, _tree

from app.utils.image_features import extract_features


CLASS_NAMES = ["Bercak_Daun", "Hawar_Daun", "Bulai_Daun"]
K_VALUES = [1, 3, 5, 7, 9]


def collect_split(split_dir: Path):
    x, y, paths = [], [], []
    for class_dir in sorted(p for p in split_dir.iterdir() if p.is_dir()):
        for image_path in sorted(class_dir.iterdir()):
            if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp"}:
                continue
            features, _ = extract_features(image_path)
            x.append(features)
            y.append(class_dir.name)
            paths.append(str(image_path))
    return np.asarray(x, dtype=np.float32), np.asarray(y), paths


def metrics(model_name, estimator, x_test, y_test, encoder, extra=None):
    pred = estimator.predict(x_test)
    labels = encoder.classes_.tolist()
    report = classification_report(
        y_test,
        pred,
        labels=np.arange(len(labels)),
        target_names=labels,
        output_dict=True,
        zero_division=0,
    )
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, pred, average="macro", zero_division=0
    )
    result = {
        "model": model_name,
        "accuracy": float(accuracy_score(y_test, pred)),
        "macro_precision": float(precision),
        "macro_recall": float(recall),
        "macro_f1": float(f1),
        "classification_report": report,
        "confusion_matrix": confusion_matrix(y_test, pred).tolist(),
    }
    if extra:
        result.update(extra)
    return result


def train_all(project_root: str | Path) -> dict:
    root = Path(project_root)
    split_root = root / "dataset" / "split"
    model_dir = root / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    x_train, y_train_text, _ = collect_split(split_root / "train")
    x_val, y_val_text, _ = collect_split(split_root / "val")
    x_test, y_test_text, _ = collect_split(split_root / "test")

    encoder = LabelEncoder()
    encoder.fit(CLASS_NAMES)
    y_train = encoder.transform(y_train_text)
    y_val = encoder.transform(y_val_text)
    y_test = encoder.transform(y_test_text)

    scaler = StandardScaler()
    x_train_s = scaler.fit_transform(x_train)
    x_val_s = scaler.transform(x_val)
    x_test_s = scaler.transform(x_test)

    joblib.dump(scaler, model_dir / "scaler.joblib")
    joblib.dump(encoder, model_dir / "label_encoder.joblib")

    validation_results = []

    c45_val = DecisionTreeClassifier(criterion="entropy", random_state=42)
    c45_val.fit(x_train_s, y_train)
    validation_results.append(metrics("c45", c45_val, x_val_s, y_val, encoder))

    gnb_val = GaussianNB()
    gnb_val.fit(x_train_s, y_train)
    validation_results.append(metrics("gaussian_nb", gnb_val, x_val_s, y_val, encoder))

    for k in K_VALUES:
        knn_val = KNeighborsClassifier(n_neighbors=k, metric="euclidean")
        knn_val.fit(x_train_s, y_train)
        validation_results.append(metrics("knn", knn_val, x_val_s, y_val, encoder, {"k": k}))

    selected = max(
        validation_results,
        key=lambda r: (r["accuracy"], r["macro_f1"], r["macro_precision"]),
    )

    # Untuk evaluasi final, model dilatih ulang menggunakan train + validation.
    x_fit = np.vstack([x_train, x_val])
    y_fit = np.concatenate([y_train, y_val])
    final_scaler = StandardScaler()
    x_fit_s = final_scaler.fit_transform(x_fit)
    x_test_final_s = final_scaler.transform(x_test)
    joblib.dump(final_scaler, model_dir / "scaler.joblib")

    # Referensi numerik untuk Form 3: citra baru dapat dibandingkan dengan
    # distribusi feature vector Train / Validation / Test tanpa mengubah
    # label evaluasi test.
    # Semua split dibandingkan dalam ruang fitur yang sama, yaitu scaler
    # final yang fit pada Train + Validation.
    x_train_final_s = final_scaler.transform(x_train)
    x_val_final_s = final_scaler.transform(x_val)
    np.savez_compressed(
        model_dir / "dataset_reference.npz",
        train=x_train_final_s, train_labels=y_train,
        val=x_val_final_s, val_labels=y_val,
        test=x_test_final_s, test_labels=y_test,
    )

    final_models = []

    c45 = DecisionTreeClassifier(criterion="entropy", random_state=42)
    t_train = perf_counter()
    c45.fit(x_fit_s, y_fit)
    c45_train_time = perf_counter() - t_train
    joblib.dump(c45, model_dir / "c45.joblib")
    feature_names = [f"f{i+1}" for i in range(x_fit_s.shape[1])]
    tree = c45.tree_
    node_rows = []
    for node_id in range(tree.node_count):
        feature_index = int(tree.feature[node_id])
        node_rows.append({
            "node": node_id,
            "feature": feature_names[feature_index] if feature_index != _tree.TREE_UNDEFINED else None,
            "threshold": None if feature_index == _tree.TREE_UNDEFINED else float(tree.threshold[node_id]),
            "samples": int(tree.n_node_samples[node_id]),
            "impurity": float(tree.impurity[node_id]),
            "is_leaf": feature_index == _tree.TREE_UNDEFINED,
        })
    t_eval = perf_counter()
    c45_result = metrics("c45", c45, x_test_final_s, y_test, encoder, {
        "tree": export_text(c45, feature_names=feature_names, max_depth=5),
        "nodes": node_rows,
        "node_count": int(tree.node_count),
        "depth": int(tree.max_depth),
        "criterion": "entropy",
        "training_time": c45_train_time,
        "evaluation_time": perf_counter() - t_eval,
        "feature_count": int(x_fit_s.shape[1]),
    })
    final_models.append(c45_result)

    gnb = GaussianNB()
    t_train = perf_counter()
    gnb.fit(x_fit_s, y_fit)
    gnb_train_time = perf_counter() - t_train
    joblib.dump(gnb, model_dir / "gaussian_nb.joblib")
    t_eval = perf_counter()
    gnb_result = metrics("gaussian_nb", gnb, x_test_final_s, y_test, encoder, {
        "class_prior": gnb.class_prior_.tolist(),
        "mean": gnb.theta_.tolist(),
        "variance": gnb.var_.tolist(),
        "training_time": gnb_train_time,
        "evaluation_time": perf_counter() - t_eval,
        "feature_count": int(x_fit_s.shape[1]),
    })
    final_models.append(gnb_result)

    for k in K_VALUES:
        knn = KNeighborsClassifier(n_neighbors=k, metric="euclidean")
        t_train = perf_counter()
        knn.fit(x_fit_s, y_fit)
        knn_train_time = perf_counter() - t_train
        joblib.dump(knn, model_dir / f"knn_k{k}.joblib")
        t_eval = perf_counter()
        knn_result = metrics("knn", knn, x_test_final_s, y_test, encoder, {
            "k": k,
            "training_time": knn_train_time,
            "evaluation_time": perf_counter() - t_eval,
            "feature_count": int(x_fit_s.shape[1]),
        })
        final_models.append(knn_result)

    # Model terbaik dipilih berdasarkan validation, bukan test, agar test tetap menjadi data evaluasi akhir.
    best_knn_val = max(
        [r for r in validation_results if r["model"] == "knn"],
        key=lambda r: (r["accuracy"], r["macro_f1"]),
    )
    # File knn.joblib selalu menunjuk ke KNN terbaik berdasarkan validation.
    best_knn = KNeighborsClassifier(n_neighbors=best_knn_val["k"], metric="euclidean")
    best_knn.fit(x_fit_s, y_fit)
    joblib.dump(best_knn, model_dir / "knn.joblib")

    from app.utils.generate_heatmaps import save_confusion_heatmap
    labels = encoder.classes_.tolist()
    for row in final_models:
        suffix = f"_k{row.get('k')}" if row.get("model") == "knn" else ""
        heatmap_path = model_dir / f"confusion_{row['model']}{suffix}.png"
        save_confusion_heatmap(
            row["confusion_matrix"],
            labels,
            heatmap_path,
            f"Confusion Matrix - {row['model']}{suffix}",
        )
        row["heatmap_path"] = str(heatmap_path.relative_to(root))

    output = {
        "selection_basis": "validation",
        "dataset": {
            "train": int(len(y_train)),
            "val": int(len(y_val)),
            "test": int(len(y_test)),
            "train_plus_val": int(len(y_fit)),
            "feature_count": int(x_train.shape[1]),
            "classes": encoder.classes_.tolist(),
        },
        "validation": validation_results,
        "models": final_models,
        "best_model": {
            "model": selected["model"],
            "k": selected.get("k"),
            "validation_accuracy": selected["accuracy"],
            "validation_macro_f1": selected["macro_f1"],
        },
    }

    (model_dir / "evaluation.json").write_text(
        json.dumps(output, indent=2), encoding="utf-8"
    )
    return output


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    split_result = __import__("app.utils.dataset_split", fromlist=["split_dataset"]).split_dataset(
        root / "dataset" / "raw", root / "dataset" / "split"
    )
    print("Split selesai:", split_result)
    result = train_all(root)
    print("Training selesai:", result["best_model"])
