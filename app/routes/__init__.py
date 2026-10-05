from app.routes.main_routes import main_bp
from app.routes.prediction_routes import prediction_bp
from app.routes.evaluation_routes import evaluation_bp
from app.routes.history_routes import history_bp
from app.routes.symptom_routes import symptom_bp
from app.routes.pwa_routes import pwa_bp

__all__ = [
    "main_bp",
    "prediction_bp",
    "evaluation_bp",
    "history_bp",
    "symptom_bp",
    "pwa_bp"
]