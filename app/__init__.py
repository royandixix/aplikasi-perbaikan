from pathlib import Path

from flask import Flask

from config import Config
from app.extensions import db


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    for key in ("DATA_ROOT", "UPLOAD_FOLDER", "PROCESSED_FOLDER", "HEATMAP_FOLDER"):
        Path(app.config[key]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)

    from app.models import (  # noqa: F401
        PredictionHistory,
        ModelEvaluation,
        ProcessingStep,
        DatasetRecord,
        DiseaseSymptom,
    )
    from app.routes.main_routes import main_bp
    from app.routes.prediction_routes import prediction_bp
    from app.routes.evaluation_routes import evaluation_bp
    from app.routes.history_routes import history_bp
    from app.routes.symptom_routes import symptom_bp
    from app.routes.pwa_routes import pwa_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(prediction_bp, url_prefix="/api/prediction")
    app.register_blueprint(evaluation_bp, url_prefix="/api/evaluation")
    app.register_blueprint(history_bp, url_prefix="/api/history")
    app.register_blueprint(symptom_bp, url_prefix="/api/symptoms")
    app.register_blueprint(pwa_bp)

    with app.app_context():
        db.create_all()
        from app.utils.seed_symptoms import seed_symptoms
        seed_symptoms()

    return app
