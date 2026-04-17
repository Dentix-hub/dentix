from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend import models
from .dependencies import get_db
from backend.services.cache_service import cached

router = APIRouter()


# --- Public System Settings ---
@router.get("/settings/public")
@cached("public_settings", expire=300)  # Cache for 5 minutes
def get_public_settings(db: Session = Depends(get_db)):
    """Fetch public system settings (e.g. Banner)."""
    settings = (
        db.query(models.SystemSetting)
        .filter(models.SystemSetting.is_public)
        .all()
    )

    return {s.key: s.value for s in settings}
