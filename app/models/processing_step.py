from app.extensions import db


class ProcessingStep(db.Model):
    __tablename__ = "processing_steps"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    prediction_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "prediction_history.id"
        ),
        nullable=False
    )

    step_name = db.Column(
        db.String(100),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    image_path = db.Column(
        db.String(500),
        nullable=True
    )

    statistics_json = db.Column(
        db.Text,
        nullable=True
    )

    step_order = db.Column(
        db.Integer,
        nullable=False
    )