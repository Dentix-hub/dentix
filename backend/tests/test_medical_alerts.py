import json
from pathlib import Path
import pytest

from backend.schemas.patient import Patient, PatientDirectoryItem, MedicalAlert
from backend.utils.medical_alerts import derive_medical_alerts, get_label_to_key_map


def test_derive_medical_alerts_empty_and_none():
    assert derive_medical_alerts(None) == {"has_alert": False, "kinds": []}
    assert derive_medical_alerts("") == {"has_alert": False, "kinds": []}
    assert derive_medical_alerts("   ") == {"has_alert": False, "kinds": []}


def test_derive_medical_alerts_none_condition():
    assert derive_medical_alerts("None") == {"has_alert": False, "kinds": []}
    assert derive_medical_alerts("none") == {"has_alert": False, "kinds": []}
    assert derive_medical_alerts("لا يوجد") == {"has_alert": False, "kinds": []}


def test_derive_medical_alerts_english_labels():
    res = derive_medical_alerts("Diabetes, Hypertension")
    assert res["has_alert"] is True
    assert set(res["kinds"]) == {"diabetes", "hypertension"}

    res_preg = derive_medical_alerts("Pregnancy/Lactation")
    assert res_preg["has_alert"] is True
    assert res_preg["kinds"] == ["pregnancy"]


def test_derive_medical_alerts_arabic_labels():
    res = derive_medical_alerts("سكري، ضغط دم")
    assert res["has_alert"] is True
    assert set(res["kinds"]) == {"diabetes", "hypertension"}

    res_preg = derive_medical_alerts("حمل")
    assert res_preg["has_alert"] is True
    assert res_preg["kinds"] == ["pregnancy"]

    res_preg2 = derive_medical_alerts("حمل/رضاعة")
    assert res_preg2["has_alert"] is True
    assert res_preg2["kinds"] == ["pregnancy"]


def test_derive_medical_alerts_mixed_labels():
    res = derive_medical_alerts("Diabetes، حساسية, smoking")
    assert res["has_alert"] is True
    assert set(res["kinds"]) == {"diabetes", "allergy", "smoking"}


def test_derive_medical_alerts_free_text():
    res = derive_medical_alerts("Severe asthma with inhaler")
    assert res["has_alert"] is True
    assert res["kinds"] == ["other"]

    res_mixed = derive_medical_alerts("Diabetes، مريض يعاني من حساسية البنسلين")
    assert res_mixed["has_alert"] is True
    assert "diabetes" in res_mixed["kinds"]
    assert "other" in res_mixed["kinds"]


def test_derive_medical_alerts_free_text_negatives():
    negatives = ["مفيش", "لا شيء", "ما فيش", "no", "none", "n/a", "-", "لا شئ", "مافيش"]
    for neg in negatives:
        res = derive_medical_alerts(neg)
        assert res["has_alert"] is False, f"Negative '{neg}' should not have alert, got {res}"
        assert res["kinds"] == [], f"Negative '{neg}' kinds should be empty, got {res}"


def test_derive_medical_alerts_smoking_alone_has_no_alert():
    res_en = derive_medical_alerts("smoking")
    assert res_en["has_alert"] is False, f"Smoking alone must not set has_alert, got {res_en}"
    assert "smoking" in res_en["kinds"]

    res_ar = derive_medical_alerts("تدخين")
    assert res_ar["has_alert"] is False, f"Smoking alone in Arabic must not set has_alert, got {res_ar}"
    assert "smoking" in res_ar["kinds"]

    res_combo = derive_medical_alerts("smoking, diabetes")
    assert res_combo["has_alert"] is True
    assert set(res_combo["kinds"]) == {"smoking", "diabetes"}



def test_locale_parity_with_frontend_translation_files():
    root = Path(__file__).resolve().parent.parent.parent
    en_path = root / "frontend" / "src" / "locales" / "en" / "translation.json"
    ar_path = root / "frontend" / "src" / "locales" / "ar" / "translation.json"

    assert en_path.exists(), f"EN locale file not found at {en_path}"
    assert ar_path.exists(), f"AR locale file not found at {ar_path}"

    with open(en_path, "r", encoding="utf-8") as f:
        en_data = json.load(f)
    with open(ar_path, "r", encoding="utf-8") as f:
        ar_data = json.load(f)

    en_conditions = en_data["patients"]["medical_conditions"]
    ar_conditions = ar_data["patients"]["medical_conditions"]

    # Every condition key in locale files (except none and smoking) should map to has_alert=True
    for key, label in en_conditions.items():
        if key == "none":
            continue
        alerts = derive_medical_alerts(label)
        expected_has_alert = (key != "smoking")
        assert alerts["has_alert"] is expected_has_alert, f"EN label '{label}' for key '{key}' should have has_alert={expected_has_alert}"
        assert key in alerts["kinds"], f"EN label '{label}' should map to key '{key}'"

    for key, label in ar_conditions.items():
        if key == "none":
            continue
        alerts = derive_medical_alerts(label)
        expected_has_alert = (key != "smoking")
        assert alerts["has_alert"] is expected_has_alert, f"AR label '{label}' for key '{key}' should have has_alert={expected_has_alert}"
        assert key in alerts["kinds"], f"AR label '{label}' should map to key '{key}'"


def test_patient_schemas_include_medical_alert():
    item = PatientDirectoryItem(
        id=1,
        file_number=1,
        name="Test Patient",
        medical_alert=MedicalAlert(has_alert=True, kinds=["pregnancy"]),
    )
    assert item.medical_alert.has_alert is True
    assert item.medical_alert.kinds == ["pregnancy"]

    patient = Patient(
        id=1,
        name="Patient Detail",
        medical_history="Diabetes, Hypertension",
    )
    assert patient.medical_alert.has_alert is True
    assert set(patient.medical_alert.kinds) == {"diabetes", "hypertension"}
