from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class IntentResult(BaseModel):
    intent: str
    confidence: float
    skip_llm: bool = False
    extracted_data: Dict[str, Any] = {}
    missing_fields: List[str] = []

class IntentDetectorInterface(ABC):
    """
    Abstract Interface for Intent Detection.
    Allows swapping between Rule-based, Regex-based, or ML-based detectors.
    """
    
    @abstractmethod
    def detect(self, text: str, context: Optional[List[Dict]] = None) -> Optional[IntentResult]:
        """
        Detect intent from user text.
        Returns IntentResult if an intent is strongly matched, else None.
        """
        pass
