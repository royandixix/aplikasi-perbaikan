from app import create_app
from app.services.symptom_service import get_symptoms_by_disease, score_symptoms


def test_symptoms():
    app = create_app()
    with app.app_context():
        symptoms = get_symptoms_by_disease()
        assert set(symptoms) >= {"Bercak_Daun", "Hawar_Daun", "Bulai_Daun"}
        assert score_symptoms("Bulai_Daun", ["BL01"]) > 0
