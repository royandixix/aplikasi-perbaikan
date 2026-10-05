from datetime import datetime
from app.extensions import db


class ModelEvaluation(db.Model):
    __tablename__ = "model_evaluations"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    model_name = db.Column(
        db.String(100),
        nullable=False
    )

    accuracy = db.Column(
        db.Float,
        nullable=False
    )

    macro_precision = db.Column(
        db.Float,
        nullable=False
    )

    macro_recall = db.Column(
        db.Float,
        nullable=False
    )

    macro_f1 = db.Column(
        db.Float,
        nullable=False
    )

    best_k = db.Column(
        db.Integer,
        nullable=True
    )

    confusion_matrix_json = db.Column(
        db.Text,
        nullable=False
    )

    classification_report_json = db.Column(
        db.Text,
        nullable=False
    )

    heatmap_path = db.Column(
        db.String(500),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )