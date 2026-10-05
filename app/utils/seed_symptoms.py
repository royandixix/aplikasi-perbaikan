from __future__ import annotations

from app.extensions import db
from app.models.disease_symptom import DiseaseSymptom


SYMPTOMS = {
    "Bercak_Daun": [
        ("BD01", "Bercak cokelat pada daun", "Muncul bercak cokelat pada permukaan daun.", 1.0),
        ("BD02", "Bercak berbentuk lonjong", "Bercak tampak memanjang atau berbentuk lonjong.", 0.9),
        ("BD03", "Daun menguning", "Sebagian jaringan daun mengalami perubahan warna menjadi kuning.", 0.7),
        ("BD04", "Jaringan daun mengalami nekrosis", "Jaringan yang terserang berubah cokelat dan mati.", 0.9),
    ],
    "Hawar_Daun": [
        ("HD01", "Lesi memanjang pada daun", "Terlihat lesi memanjang berwarna cokelat pada daun.", 1.0),
        ("HD02", "Bercak hijau keabu-abuan", "Terdapat area hijau keabu-abuan pada permukaan daun.", 0.9),
        ("HD03", "Daun mengering", "Jaringan daun menjadi kering pada area yang terserang.", 0.8),
        ("HD04", "Kerusakan meluas dari ujung daun", "Kerusakan dapat berkembang dari bagian ujung daun.", 0.8),
    ],
    "Bulai_Daun": [
        ("BL01", "Daun berwarna kuning pucat", "Daun mengalami perubahan warna menjadi kuning pucat.", 1.0),
        ("BL02", "Garis kuning pada daun", "Terlihat pola garis kekuningan pada permukaan daun.", 0.9),
        ("BL03", "Pertumbuhan tanaman terhambat", "Tanaman menunjukkan pertumbuhan yang tidak optimal.", 0.8),
        ("BL04", "Lapisan putih atau keabu-abuan", "Pada kondisi tertentu tampak lapisan pada permukaan daun.", 0.9),
    ],
}


def seed_symptoms() -> None:
    for disease, items in SYMPTOMS.items():
        for code, name, description, weight in items:
            record = DiseaseSymptom.query.filter_by(symptom_code=code).first()
            if record is None:
                record = DiseaseSymptom(symptom_code=code)
                db.session.add(record)
            record.disease_class = disease
            record.symptom_name = name
            record.description = description
            record.weight = weight
            record.is_active = True
    db.session.commit()
