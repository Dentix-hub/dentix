from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend import models, schemas
from fastapi import HTTPException


class FeatureFlagService:
    @staticmethod
    async def is_feature_enabled(db: AsyncSession, key: str, tenant_id: int = None) -> bool:
        """
        Determines if a feature is enabled.
        Priority:
        1. Tenant Override (if tenant_id provided)
        2. Global Flag
        3. Default False
        """
        # 1. Check Tenant Override
        if tenant_id:
            stmt = select(models.TenantFeature).where(
                models.TenantFeature.tenant_id == tenant_id,
                models.TenantFeature.feature_key == key,
            )
            override = (await db.execute(stmt)).scalar_one_or_none()
            if override:
                return override.is_enabled

        # 2. Check Global Flag
        stmt = select(models.FeatureFlag).where(models.FeatureFlag.key == key)
        flag = (await db.execute(stmt)).scalar_one_or_none()
        if not flag:
            return False  # Feature doesn't exist -> Disabled by default (Fail-safe)

        if not flag.is_global_enabled:
            return False

        # 3. Check Rollout Percentage (if not 100/0)
        if 0 < flag.rollout_percentage < 100:
            if tenant_id:
                # Deterministic rollout based on Tenant ID
                # Effectively: if tenant_id % 100 < percentage
                return (tenant_id % 100) < flag.rollout_percentage
            else:
                # No context for rollout, default to enabled if global is true
                # OR randomly decide (not recommended for consistecy)
                # Let's fallback to True since is_global_enabled is True here
                return True

        return True

    @staticmethod
    async def create_flag(db: AsyncSession, flag_data: schemas.FeatureFlagCreate):
        stmt = select(models.FeatureFlag).where(models.FeatureFlag.key == flag_data.key)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Feature flag already exists")

        new_flag = models.FeatureFlag(**flag_data.model_dump())
        db.add(new_flag)
        await db.commit()
        await db.refresh(new_flag)
        return new_flag

    @staticmethod
    async def update_flag(db: AsyncSession, key: str, update_data: dict):
        stmt = select(models.FeatureFlag).where(models.FeatureFlag.key == key)
        flag = (await db.execute(stmt)).scalar_one_or_none()
        if not flag:
            raise HTTPException(status_code=404, detail="Feature flag not found")

        for k, v in update_data.items():
            setattr(flag, k, v)

        await db.commit()
        await db.refresh(flag)
        return flag

    @staticmethod
    async def set_tenant_override(db: AsyncSession, tenant_id: int, key: str, is_enabled: bool):
        # Ensure flag exists
        stmt = select(models.FeatureFlag).where(models.FeatureFlag.key == key)
        flag = (await db.execute(stmt)).scalar_one_or_none()
        if not flag:
            raise HTTPException(status_code=404, detail="Feature flag not found")

        stmt = select(models.TenantFeature).where(
            models.TenantFeature.tenant_id == tenant_id,
            models.TenantFeature.feature_key == key,
        )
        override = (await db.execute(stmt)).scalar_one_or_none()

        if override:
            override.is_enabled = is_enabled
        else:
            override = models.TenantFeature(
                tenant_id=tenant_id, feature_key=key, is_enabled=is_enabled
            )
            db.add(override)

        await db.commit()
        return override

    @staticmethod
    async def get_all_flags(db: AsyncSession):
        stmt = select(models.FeatureFlag)
        res = await db.execute(stmt)
        return list(res.scalars().all())
