from flask import Blueprint, jsonify

from app.services.symptom_service import get_symptoms_by_disease

symptom_bp = Blueprint("symptom", __name__)


@symptom_bp.get("/")
def symptoms():
    return jsonify({"success": True, "data": get_symptoms_by_disease()})
