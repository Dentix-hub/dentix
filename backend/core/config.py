import os

API_V1_STR = "/api/v1"


def get_cors_origins():
    env_origins = os.getenv("CORS_ORIGINS")
    if env_origins:
        return [origin.strip() for origin in env_origins.split(",")]

    return [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]


def get_allow_origin_regex():
    if os.getenv("ENVIRONMENT") != "production":
        return r"http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+):\d+"
    return None


def is_ai_read_only() -> bool:
    """
    Check if AI is in Read-Only mode.
    Defaults to False unless explicitly set to 'true'.
    """
    return os.getenv("AI_READ_ONLY", "false").lower() == "true"


def is_ai_disabled() -> bool:
    """
    Kill Switch: Globally disable AI features.
    Configured via env 'AI_GLOBAL_DISABLE=true'.
    """
    return os.getenv("AI_GLOBAL_DISABLE", "false").lower() == "true"
