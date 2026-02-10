"""
AI Validation Layer.
Handles input scrubbing (PII) and struct validation before AI processing.
Acts as a security gatekeeper.
"""

from typing import Dict, Tuple, Any
from backend.ai.privacy.scrubber import scrubber
from backend.ai.errors import AIValidationError
import re


class AIValidationLayer:
    """
    Validates and sanitizes input for the AI system.
    """

    MAX_INPUT_LENGTH = 2000
    INJECTION_KEYWORDS = [
        "ignore previous instructions",
        "forget all instructions",
        "system prompt",
        "you are a hacked",
        "bypass mode",
    ]

    @staticmethod
    def validate_request(text: str) -> None:
        """
        Validate raw user request.
        Raises AIValidationError if invalid.
        """
        if not text or not text.strip():
            raise AIValidationError("النص المدخل فارغ", code="input_empty")

        if len(text) > AIValidationLayer.MAX_INPUT_LENGTH:
            raise AIValidationError(
                f"النص طويل جداً (الحد الأقصى {AIValidationLayer.MAX_INPUT_LENGTH} حرف)",
                code="input_too_long",
            )

        # Basic Injection Detection
        text_lower = text.lower()
        for keyword in AIValidationLayer.INJECTION_KEYWORDS:
            if keyword in text_lower:
                # We log this ideally, but for now just block
                raise AIValidationError(
                    "تم رفض الطلب لأسباب أمنية (نمط غير مسموح)",
                    code="security_risk",
                    debug_info={"pattern": keyword},
                )

    @staticmethod
    def scrub_input(text: str) -> Tuple[str, Dict[str, str]]:
        """
        Scrub PII from input text.
        Returns: (safe_text, aliases_map)
        """
        return scrubber.scrub(text)

    @staticmethod
    def restore_output(text: str, aliases: Dict[str, str]) -> str:
        """
        Restore PII in output text.
        """
        return scrubber.restore(text, aliases)

    @staticmethod
    def validate_patient_data(data: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate patient data before creation.
        Returns dict of errors (empty if valid).
        """
        errors = {}

        name = data.get("patient_name")
        phone = data.get("phone")
        age = data.get("age")

        if not name:
            errors["patient_name"] = "اسم المريض مطلوب"
        elif len(name.split()) < 2:
            errors["patient_name"] = "الاسم يجب أن يكون ثنائي على الأقل"

        if not phone:
            errors["phone"] = "رقم الهاتف مطلوب"
        elif not re.match(r"^\d{10,12}$", phone):
            # Simple check for 10-12 digits
            pass

        if age is None:
            errors["age"] = "السن مطلوب"
        else:
            try:
                age_int = int(age)
                if age_int < 0 or age_int > 120:
                    errors["age"] = "السن غير منطقي"
            except:
                errors["age"] = "السن يجب أن يكون رقم"

        return errors
