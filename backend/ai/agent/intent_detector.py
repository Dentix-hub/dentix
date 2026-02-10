"""
Intent Detector Module
Pre-processes user input to detect clear intents before LLM.
Bypasses LLM for high-confidence cases to improve accuracy.
"""

import re
from typing import Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class DetectedIntent:
    """Result of intent detection."""

    intent: str
    confidence: float  # 0.0 to 1.0
    extracted_data: Dict[str, Any]
    skip_llm: bool  # If True, skip LLM entirely


class IntentDetector:
    """
    Keyword-based intent detection.
    Runs BEFORE the LLM to catch clear patterns.
    """

    # Patient Registration Keywords (Arabic)
    PATIENT_REGISTRATION_KEYWORDS = [
        "سجل مريض",
        "ضيف مريض",
        "مريض جديد",
        "افتح ملف",
        "اضف مريض",
        "مريضه جديده",  # Normalized teh marbuta to heh -> ha
        "مريضه جديدة",  # Just in case
        "سجلي مريض",
        "ضيفي مريض",
    ]

    # Payment Keywords (must have amount)
    PAYMENT_KEYWORDS = ["دفع", "سدد", "المريض دفع", "دفعت", "سددت"]

    # Appointment Keywords
    APPOINTMENT_KEYWORDS = ["موعد", "حجز", "احجز", "احجزي"]

    def detect(
        self, user_input: str, context: Optional[Dict] = None
    ) -> Optional[DetectedIntent]:
        """
        Analyze user input and detect intent.
        Returns None if no clear intent detected (let LLM decide).
        """
        from backend.ai.utils.normalization import normalizer

        # Normalize input
        text = normalizer.normalize(user_input)

        # 1. Check for Patient Registration
        patient_intent = self._detect_patient_registration(text)
        if patient_intent:
            return patient_intent

        # 2. Future: Add more intent detectors here
        # payment_intent = self._detect_payment(text)
        # appointment_intent = self._detect_appointment(text)

        return None  # Let LLM handle

    def _detect_patient_registration(self, text: str) -> Optional[DetectedIntent]:
        """Detect patient registration intent with confidence scoring."""

        # Check if any keyword matches
        matched = any(kw in text for kw in self.PATIENT_REGISTRATION_KEYWORDS)
        if not matched:
            return None

        # Extract data
        name = self._extract_patient_name(text)
        phone = self._extract_phone(text)
        age = self._extract_age(text)

        extracted = {"patient_name": name, "phone": phone, "age": age}

        # Scoring Logic
        score = 0.5  # Base score for keyword match

        if name:
            score += 0.3
        if phone:
            score += 0.1
        if age:
            score += 0.1

        # Context Boost (e.g. if name is long enough)
        if name and len(name.split()) >= 3:
            score += 0.05

        # Cap score at 1.0
        score = min(score, 1.0)

        # Decision
        # >= 0.85 -> Execute (High)
        # 0.60 - 0.85 -> Confirm (Medium)
        # < 0.60 -> LLM (Low) - but here if we return None, it goes to LLM.
        # However, we want to return the intent so core.py can decide.

        return DetectedIntent(
            intent="patient_registration",
            confidence=score,
            extracted_data=extracted,
            skip_llm=score >= 0.60,  # Only skip LLM if we are at least reasonably sure
        )

    def _extract_patient_name(self, text: str) -> Optional[str]:
        """Extract patient name from text."""
        # Patterns: "اسمه X", "اسمها X", "باسم X", "المريض X"
        patterns = [
            r"(?:اسم[هو]ا?|باسم|المريض|المريضة)\s+([^\d,،\.\؟\?]+?)(?:\s+(?:عمر|سن|رقم|تليفون|$))",
            r"(?:سجل|ضيف|أضف|اضف)\s+(?:مريض|مريضة)?\s*(?:جديد|جديدة)?\s*(?:اسم[هو]ا?|باسم)?\s*([^\d,،\.\؟\?]+?)(?:\s+(?:عمر|سن|رقم|تليفون|$))",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                # Clean up common suffixes
                name = re.sub(r"\s+(عمره?|سنه?|ورقم|تليفون).*$", "", name)
                if len(name) >= 3:  # Minimum name length
                    return name

        # Fallback: Try to find name after keywords
        for kw in self.PATIENT_REGISTRATION_KEYWORDS:
            if kw in text:
                after_kw = text.split(kw, 1)[-1].strip()
                # Take first 2-3 words as name
                words = after_kw.split()[:3]
                # Filter out numbers and common words
                name_words = [
                    w
                    for w in words
                    if not re.match(r"^\d+$", w)
                    and w not in ["عمره", "سنه", "ورقمه", "رقمه"]
                ]
                if name_words:
                    return " ".join(name_words)

        return None

    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from text."""
        # Egyptian phone patterns: 01xxxxxxxxx
        match = re.search(r"(01[0-9]{9})", text)
        if match:
            return match.group(1)

        # With spaces or dashes
        match = re.search(r"(01[0-9][\s\-]?[0-9]{3}[\s\-]?[0-9]{4})", text)
        if match:
            return re.sub(r"[\s\-]", "", match.group(1))

        return None

    def _extract_age(self, text: str) -> Optional[int]:
        """Extract age from text."""
        # Patterns: "عمره 35", "سنه 35", "35 سنة"
        patterns = [
            r"(?:عمر|سن)[هو]?[اى]?\s*(\d{1,3})",  # Matches "سن 30", "عمره 30", "عمرها 30"
            r"(\d{1,3})\s*(?:سنة?|سنه|عام)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                age = int(match.group(1))
                if 0 < age <= 120:
                    return age

        return None


# Singleton
_detector = None


def get_intent_detector() -> IntentDetector:
    global _detector
    if _detector is None:
        _detector = IntentDetector()
    return _detector
