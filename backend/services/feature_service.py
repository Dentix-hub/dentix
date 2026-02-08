from sqlalchemy.orm import Session
from backend import models, schemas
from fastapi import HTTPException
import random

class FeatureFlagService:
    @staticmethod
    def is_feature_enabled(db: Session, key: str, tenant_id: int = None) -> bool:
        """
        Determines if a feature is enabled.
        Priority:
        1. Tenant Override (if tenant_id provided)
        2. Global Flag
        3. Default False
        """
        # 1. Check Tenant Override
        if tenant_id:
            override = db.query(models.TenantFeature).filter(
                models.TenantFeature.tenant_id == tenant_id,
                models.TenantFeature.feature_key == key
            ).first()
            if override:
                return override.is_enabled

        # 2. Check Global Flag
        flag = db.query(models.FeatureFlag).filter(models.FeatureFlag.key == key).first()
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
    def create_flag(db: Session, flag_data: schemas.FeatureFlagCreate):
        existing = db.query(models.FeatureFlag).filter(models.FeatureFlag.key == flag_data.key).first()
        if existing:
            raise HTTPException(status_code=400, detail="Feature flag already exists")
        
        new_flag = models.FeatureFlag(**flag_data.model_dump())
        db.add(new_flag)
        db.commit()
        db.refresh(new_flag)
        return new_flag

    @staticmethod
    def update_flag(db: Session, key: str, update_data: dict):
        flag = db.query(models.FeatureFlag).filter(models.FeatureFlag.key == key).first()
        if not flag:
            raise HTTPException(status_code=404, detail="Feature flag not found")
        
        for k, v in update_data.items():
            setattr(flag, k, v)
        
        db.commit()
        db.refresh(flag)
        return flag

    @staticmethod
    def set_tenant_override(db: Session, tenant_id: int, key: str, is_enabled: bool):
        # Ensure flag exists
        flag = db.query(models.FeatureFlag).filter(models.FeatureFlag.key == key).first()
        if not flag:
            raise HTTPException(status_code=404, detail="Feature flag not found")

        override = db.query(models.TenantFeature).filter(
            models.TenantFeature.tenant_id == tenant_id,
            models.TenantFeature.feature_key == key
        ).first()

        if override:
            override.is_enabled = is_enabled
        else:
            override = models.TenantFeature(
                tenant_id=tenant_id,
                feature_key=key,
                is_enabled=is_enabled
            )
            db.add(override)
        
        db.commit()
        return override

    @staticmethod
    def get_all_flags(db: Session):
        return db.query(models.FeatureFlag).all()
