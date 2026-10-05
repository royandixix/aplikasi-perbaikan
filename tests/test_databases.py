from app import create_app
from app.extensions import db
from app.models.disease_symptom import DiseaseSymptom


def test_database_and_symptoms():
    app = create_app()
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
    with app.app_context():
        db.create_all()
        assert DiseaseSymptom.query.count() >= 12
