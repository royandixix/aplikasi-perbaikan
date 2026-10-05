from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "corn-disease-development-key")

    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'instance' / 'corn_disease.sqlite3'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

    # Semua artefak runtime disimpan di folder data milik project.
    # Tidak pernah menggunakan path absolut dari komputer pengguna sebagai URL.
    DATA_ROOT = BASE_DIR / "data"
    UPLOAD_FOLDER = DATA_ROOT / "uploads"
    PROCESSED_FOLDER = DATA_ROOT / "processed"
    HEATMAP_FOLDER = DATA_ROOT / "heatmaps"

    DATASET_RAW = BASE_DIR / "dataset" / "raw"
    DATASET_SPLIT = BASE_DIR / "dataset" / "split"
    MODEL_FOLDER = BASE_DIR / "models"
    CERTIFICATE_FILE = BASE_DIR / "certificates" / "corn-disease.pem"
    KEY_FILE = BASE_DIR / "certificates" / "corn-disease-key.pem"

    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "bmp"}
    IMAGE_SIZE = (224, 224)
    CLASS_NAMES = ["Bercak_Daun", "Hawar_Daun", "Bulai_Daun"]
    RANDOM_STATE = 42
    TEST_SIZE = 0.15
    VALIDATION_SIZE = 0.15
    TRAIN_SIZE = 0.70
    K_VALUES = [1, 3, 5, 7, 9]
