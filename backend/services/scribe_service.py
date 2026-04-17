import logging
import os
import json
from typing import Dict, Any, List
from groq import Groq

logger = logging.getLogger(__name__)


class ScribeService:
    """
    Handles Medical Dictation Analysis using LLMs (Groq).
    """

    SYSTEM_PROMPT = """You are an expert AI Dental Scribe for "Smart Dent Clinic". Your task is to extract dental procedures and diagnoses from unstructured natural language and convert them into a strict JSON format.

OUTPUT FORMAT:
Return a SINGLE JSON object containing a list called "procedures".
{
  "procedures": [
    {
      "tooth_fdi": integer,        // ISO 3950 (FDI).
      "diagnosis": string,         // e.g., "Caries".
      "treatment": string,         // e.g., "Restoration".
      "surfaces": string,          // e.g., "MOD".
      "status": string             // "planned" or "completed".
    }
  ]
}

RULES:
1. Parse Arabic/English/Franco.
2. Convert Universal/Quadrants to FDI.
3. Default status is "completed".
"""

    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY")
        self.client = Groq(api_key=self.api_key) if self.api_key else None

    def analyze_dictation(self, text: str) -> List[Dict[str, Any]]:
        """Parse text into structured dental procedures."""
        if not self.client:
            raise ValueError("Groq API Key not configured")

        try:
            completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                model="llama3-70b-8192",
                temperature=0,
                response_format={"type": "json_object"},
            )

            result_json = completion.choices[0].message.content
            parsed = json.loads(result_json)
            return parsed.get("procedures", [])

        except Exception as e:
            logger.error("Scribe LLM Error: %s", e, exc_info=True)
            raise e
