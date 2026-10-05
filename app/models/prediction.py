from datetime import datetime
from app.extensions import db


class PredictionHistory(db.Model):
    __tablename__ = "prediction_history"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    image_name = db.Column(
        db.String(255),
        nullable=False
    )

    image_path = db.Column(
        db.String(500),
        nullable=False
    )

    predicted_class = db.Column(
        db.String(100),
        nullable=False
    )

    confidence = db.Column(
        db.Float,
        nullable=True
    )

    selected_model = db.Column(
        db.String(100),
        nullable=False
    )

    symptoms_json = db.Column(
        db.Text,
        nullable=True
    )

    symptom_scores_json = db.Column(
        db.Text,
        nullable=True
    )

    all_predictions_json = db.Column(
        db.Text,
        nullable=True
    )

    processing_json = db.Column(
        db.Text,
        nullable=True
    )

    feature_vector_json = db.Column(
        db.Text,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )