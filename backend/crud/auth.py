from sqlalchemy.orm import Session
from sqlalchemy import func
from backend import models, schemas


# --- Tenant CRUD ---
def get_tenant_by_name(db: Session, name: str):
    return db.query(models.Tenant).filter(models.Tenant.name == name).first()


def create_tenant(db: Session, tenant: schemas.TenantCreate):
    db_tenant = models.Tenant(
        name=tenant.name,
        subscription_status=tenant.subscription_status,
        logo=tenant.logo,
    )
    db.add(db_tenant)
    db.commit()
    db.refresh(db_tenant)
    return db_tenant


# --- User CRUD ---
def get_user(db: Session, username: str):
    """Search by Email (Priority) OR Username."""
    return (
        db.query(models.User)
        .filter(
            (func.lower(models.User.email) == username.lower())
            | (func.lower(models.User.username) == username.lower())
        )
        .first()
    )


def get_user_by_email(db: Session, email: str):
    return (
        db.query(models.User)
        .filter(func.lower(models.User.email) == email.lower())
        .first()
    )


def get_user_by_id(db: Session, user_id: int, tenant_id: int):
    return (
        db.query(models.User)
        .filter(models.User.id == user_id, models.User.tenant_id == tenant_id)
        .first()
    )


def create_user(db: Session, user: schemas.User, password_hash: str, tenant_id: int):
    db_user = models.User(
        username=user.username,
        hashed_password=password_hash,
        role=user.role,
        permissions=user.permissions,
        tenant_id=tenant_id,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_users(
    db: Session, tenant_id: int, skip: int = 0, limit: int = 100, role: str = None
):
    query = db.query(models.User).filter(models.User.tenant_id == tenant_id)
    if role:
        query = query.filter(models.User.role == role)
    return query.offset(skip).limit(limit).all()


def update_user(
    db: Session, user_id: int, user_update: schemas.UserUpdate, tenant_id: int
):
    db_user = (
        db.query(models.User)
        .filter(models.User.id == user_id, models.User.tenant_id == tenant_id)
        .first()
    )
    if db_user:
        update_data = user_update.dict(exclude_unset=True)
        # Handle password hashing if provided
        if "password" in update_data and update_data["password"]:
            from backend.auth import get_password_hash

            update_data["hashed_password"] = get_password_hash(
                update_data.pop("password")
            )

        for key, value in update_data.items():
            setattr(db_user, key, value)

        db.commit()
        db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int, tenant_id: int):
    user = (
        db.query(models.User)
        .filter(models.User.id == user_id, models.User.tenant_id == tenant_id)
        .first()
    )
    if user:
        db.delete(user)
        db.commit()
    return user
