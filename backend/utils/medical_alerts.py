import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("smart_clinic")

# Core condition keys supported in Dentix
KNOWN_CONDITION_KEYS = {
    "none",
    "diabetes",
    "hypertension",
    "heart_disease",
    "allergy",
    "blood_thinners",
    "hepatitis_c",
    "thyroid",
    "pregnancy",
    "smoking",
}

# Static fallback labels to guarantee functionality in headless/container environments
DEFAULT_LABEL_TO_KEY: Dict[str, str] = {
    # English
    "none": "none",
    "no": "none",
    "n/a": "none",
    "na": "none",
    "nil": "none",
    "nothing": "none",
    "-": "none",
    "--": "none",
    "—": "none",
    "diabetes": "diabetes",
    "hypertension": "hypertension",
    "heart disease": "heart_disease",
    "allergy": "allergy",
    "blood thinners": "blood_thinners",
    "hepatitis c": "hepatitis_c",
    "thyroid": "thyroid",
    "pregnancy": "pregnancy",
    "pregnancy/lactation": "pregnancy",
    "smoking": "smoking",
    # Arabic
    "لا يوجد": "none",
    "لايوجد": "none",
    "لا توجد": "none",
    "مفيش": "none",
    "ما فيش": "none",
    "مافيش": "none",
    "لا شيء": "none",
    "لا شئ": "none",
    "سليم": "none",
    "سكري": "diabetes",
    "ضغط دم": "hypertension",
    "ضغط الدم": "hypertension",
    "أمراض القلب": "heart_disease",
    "امراض القلب": "heart_disease",
    "أزمة قلبية": "heart_disease",
    "ازمة قلبية": "heart_disease",
    "حساسية": "allergy",
    "سيولة دم": "blood_thinners",
    "سيولة الدم": "blood_thinners",
    "فيروس سي": "hepatitis_c",
    "غدة درقية": "thyroid",
    "الغدة الدرقية": "thyroid",
    "حمل": "pregnancy",
    "حمل/رضاعة": "pregnancy",
    "حمل / رضاعة": "pregnancy",
    "تدخين": "smoking",
}


def _normalize_token(text: str) -> str:
    """Normalize text for consistent label matching across locales."""
    text = text.strip().lower()
    # Normalize Arabic alef variants
    text = re.sub(r"[إأآا]", "ا", text)
    # Normalize teh marbuta to heh
    text = re.sub(r"ة", "ه", text)
    # Normalize yaa / alef maksura
    text = re.sub(r"ى", "ي", text)
    # Normalize multiple whitespace characters
    text = re.sub(r"\s+", " ", text)
    return text


def get_label_to_key_map() -> Dict[str, str]:
    """
    Build label-to-key dictionary from frontend locale files when available,
    falling back to built-in translations.
    """
    mapping: Dict[str, str] = {
        _normalize_token(lbl): key for lbl, key in DEFAULT_LABEL_TO_KEY.items()
    }

    try:
        root = Path(__file__).resolve().parent.parent.parent
        en_file = root / "frontend" / "src" / "locales" / "en" / "translation.json"
        ar_file = root / "frontend" / "src" / "locales" / "ar" / "translation.json"

        if en_file.is_file():
            with open(en_file, "r", encoding="utf-8") as f:
                en_data = json.load(f)
                en_mc = en_data.get("patients", {}).get("medical_conditions", {})
                for k, v in en_mc.items():
                    mapping[_normalize_token(v)] = k

        if ar_file.is_file():
            with open(ar_file, "r", encoding="utf-8") as f:
                ar_data = json.load(f)
                ar_mc = ar_data.get("patients", {}).get("medical_conditions", {})
                for k, v in ar_mc.items():
                    mapping[_normalize_token(v)] = k
                # Secondary medical_conditions block if present
                ar_mc2 = ar_data.get("medical_conditions", {})
                for k, v in ar_mc2.items():
                    mapping[_normalize_token(v)] = k
    except Exception as e:
        logger.debug("Failed reading locale files for medical alerts: %s", e)

    return mapping


_LABEL_MAP: Dict[str, str] = get_label_to_key_map()


def derive_medical_alerts(medical_history: Optional[str]) -> Dict[str, Any]:
    """
    Derive structured medical alert flags from free-text medical history.

    Returns:
        {
            "has_alert": bool,
            "kinds": list[str]  # e.g. ["diabetes", "pregnancy", "other"]
        }
    """
    if not medical_history or not medical_history.strip():
        return {"has_alert": False, "kinds": []}

    # Split on English and Arabic separators (, ، ; \n \r)
    tokens = [t.strip() for t in re.split(r"[,،;\n\r]+", medical_history) if t.strip()]
    if not tokens:
        return {"has_alert": False, "kinds": []}

    kinds: List[str] = []

    for raw_token in tokens:
        norm = _normalize_token(raw_token)
        if not norm or re.match(r"^[-—_/.\s]+$", norm):
            continue

        key = _LABEL_MAP.get(norm)
        if key == "none":
            continue
        elif key:
            if key not in kinds:
                kinds.append(key)
        else:
            # Free text that matches no known label
            if "other" not in kinds:
                kinds.append("other")

    has_alert = any(k not in ("none", "smoking") for k in kinds)
    return {
        "has_alert": has_alert,
        "kinds": kinds,
    }
