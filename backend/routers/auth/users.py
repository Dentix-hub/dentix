from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend import models, schemas, auth  # auth needed for password hash
from .dependencies import get_db, get_current_user

router = APIRouter()


# --- User Profile ---
@router.put("/users/me")
def update_user_me(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user profile (email, password)."""

    # Reload user to attach to session
    user = db.query(models.User).filter(models.User.id == current_user.id).first()

    if user_update.email:
        user.email = user_update.email

    if user_update.password:
        user.hashed_password = auth.get_password_hash(user_update.password)

    db.commit()
    db.refresh(user)
    return user


@router.get("/users/me", response_model=schemas.User)
def get_user_me(current_user: models.User = Depends(get_current_user)):
    """Get current user details."""
    return current_user
