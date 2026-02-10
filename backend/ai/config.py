"""
AI System Configuration
Centralized configuration for models, limits, and costs.
"""

# =========================================================
# MODEL DEFINITIONS & COSTS
# =========================================================
# Cost per 1M tokens (Input/Output)
MODEL_CARDS = {
    "llama-3.3-70b-versatile": {
        "provider": "Groq",
        "context_window": 32768,
        "input_cost": 0.59,  # $ per 1M tokens (approx market rate)
        "output_cost": 0.79,
        "type": "complex",
    },
    "llama-3.1-8b-instant": {
        "provider": "Groq",
        "context_window": 8192,
        "input_cost": 0.05,  # Very cheap
        "output_cost": 0.10,
        "type": "fast",
    },
}

DEFAULT_MODEL = "llama-3.1-8b-instant"
COMPLEX_MODEL = "llama-3.3-70b-versatile"

# =========================================================
# SYSTEM LIMITS
# =========================================================
MAX_RETRIES = 2
MAX_HISTORY_MESSAGES = 10
RAG_SEARCH_LIMIT = 3
RAG_MIN_SCORE = 0.7

# Rate Limiting (per user per day)
QUOTA_LIMITS = {"trial": 50, "basic": 200, "pro": 1000, "enterprise": 10000}

# =========================================================
# ROUTING CONFIGURATION
# =========================================================
COMPLEX_KEYWORDS = [
    "قارن",
    "مقارنة",
    "compare",
    "حلل",
    "تحليل",
    "analyze",
    "analysis",
    "شرح",
    "اشرح",
    "explain",
    "خطة",
    "plan",
    "اكتب",
    "write",
    "draft",
    "مشكلة",
    "debug",
    "fix",
    "سبب",
    "why",
    "reason",
    "تفاصيل",
    "details",
    "لخص",
    "تلخيص",
    "summarize",
    "summary",
    "توقع",
    "predict",
    "forecast",
]

# Tools that ALWAYS require complex model
COMPLEX_TOOLS = [
    "parse_medical_dictation",
    "add_treatment_voice",  # Requiring extraction from messier inputs
    "analyze_financial_report",
    "generate_marketing_content",
]
