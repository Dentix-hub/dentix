from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from backend import models, schemas
from sqlalchemy.orm import selectinload

def normalize_username(username: str) -> str:
    """Normalize username: trim, lowercase, and basic Arabic normalization."""
    if not username:
        return ""
    u = username.strip().lower()
    # Basic Arabic normalization (Alef variants, Teh Marbuta, Yeh)
    u = u.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    u = u.replace("ة", "ه").replace("ى", "ي")
    return u


def sql_normalize_username(column):
    """Build a SQL expression equivalent to normalize_username(column)."""
    expr = func.lower(func.trim(column))
    for src, dst in (
        ("أ", "ا"),
        ("إ", "ا"),
        ("آ", "ا"),
        ("ة", "ه"),
        ("ى", "ي"),
    ):
        expr = func.replace(expr, src, dst)
    return expr


def validate_and_trim_username(username: str | None) -> str:
    """Validate and trim username without lowercasing or Arabic-normalizing the stored display value."""
    from fastapi import HTTPException

    if username is None or not username.strip():
        raise HTTPException(
            status_code=400,
            detail="اسم المستخدم لا يمكن أن يكون فارغاً",
        )
    trimmed = username.strip()
    if any(ch.isspace() for ch in trimmed):
        raise HTTPException(
            status_code=400,
            detail="اسم المستخدم لا يجب أن يحتوي على مسافات داخلية",
        )
    return trimmed


# --- Tenant CRUD ---
async def get_tenant_by_name(db: AsyncSession, name: str):
    stmt = select(models.Tenant).where(models.Tenant.name == name)
    result = await db.execute(stmt)
    return result.scalars().first()


async def create_tenant(db: AsyncSession, tenant: schemas.TenantCreate):
    db_tenant = models.Tenant(
        name=tenant.name,
        subscription_status=tenant.subscription_status,
        logo=tenant.logo,
    )
    db.add(db_tenant)
    await db.commit()
    await db.refresh(db_tenant)
    return db_tenant


# --- User CRUD ---
async def get_user(db: AsyncSession, username: str):
    """Search by Email (Priority) OR Username."""
    clean_username = normalize_username(username)
    stmt = (
        select(models.User)
        .where(
            (func.lower(func.trim(models.User.email)) == clean_username)
            | (sql_normalize_username(models.User.username) == clean_username)
        )
        .options(selectinload(models.User.tenant))
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str):
    stmt = select(models.User).where(func.lower(models.User.email) == email.lower())
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: int, tenant_id: int):
    stmt = select(models.User).where(models.User.id == user_id, models.User.tenant_id == tenant_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def create_user(db: AsyncSession, user: schemas.User, password_hash: str, tenant_id: int):
    trimmed_username = validate_and_trim_username(user.username)
    db_user = models.User(
        username=trimmed_username,
        full_name=user.full_name,
        hashed_password=password_hash,
        role=user.role,
        permissions=user.permissions,
        patient_visibility_mode=user.patient_visibility_mode or "all_assigned",
        tenant_id=tenant_id,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_users(
    db: AsyncSession, tenant_id: int, skip: int = 0, limit: int = 100, role: str = None
):
    stmt = select(models.User).where(models.User.tenant_id == tenant_id).options(
        selectinload(models.User.tenant).selectinload(models.Tenant.subscription_plan)
    )
    if role:
        stmt = stmt.where(models.User.role == role)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def update_user(
    db: AsyncSession, user_id: int, user_update: schemas.UserUpdate, tenant_id: int
):
    stmt = select(models.User).where(models.User.id == user_id, models.User.tenant_id == tenant_id)
    result = await db.execute(stmt)
    db_user = result.scalars().first()
    if db_user:
        update_data = user_update.dict(exclude_unset=True)
        if "username" in update_data:
            update_data["username"] = validate_and_trim_username(update_data["username"])
        # Handle password hashing if provided
        if "password" in update_data and update_data["password"]:
            from backend.auth import get_password_hash

            update_data["hashed_password"] = get_password_hash(
                update_data.pop("password")
            )

        for key, value in update_data.items():
            setattr(db_user, key, value)

        await db.commit()
        await db.refresh(db_user)
    return db_user


async def delete_user(db: AsyncSession, user_id: int, tenant_id: int):
    stmt = select(models.User).where(models.User.id == user_id, models.User.tenant_id == tenant_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if user:
        await db.delete(user)
        await db.commit()
    return user
