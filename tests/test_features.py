from pathlib import Path

from app.utils.image_features import extract_features


def test_extract_features():
    image = next((Path("dataset/raw/Bercak_Daun")).glob("*.jpg"))
    vector, metadata = extract_features(image)
    assert len(vector) > 0
    assert len(vector) == len(metadata["feature_names"])
    assert metadata["entropy"] >= 0
