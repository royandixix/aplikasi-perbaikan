from app.extensions import db


class DiseaseSymptom(db.Model):
    __tablename__ = "disease_symptoms"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    disease_class = db.Column(
        db.String(100),
        nullable=False
    )

    symptom_code = db.Column(
        db.String(50),
        nullable=False,
        unique=True
    )

    symptom_name = db.Column(
        db.String(255),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    weight = db.Column(
        db.Float,
        default=1.0
    )

    is_active = db.Column(
        db.Boolean,
        default=True
    )