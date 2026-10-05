from app.extensions import db


class DatasetRecord(db.Model):
    __tablename__ = "dataset_records"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    file_name = db.Column(
        db.String(255),
        nullable=False
    )

    file_path = db.Column(
        db.String(500),
        nullable=False
    )

    class_name = db.Column(
        db.String(100),
        nullable=False
    )

    split_name = db.Column(
        db.String(20),
        nullable=False
    )

    is_augmented = db.Column(
        db.Boolean,
        default=False
    )

    feature_count = db.Column(
        db.Integer,
        nullable=True
    )