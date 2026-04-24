"""
Admin Service for Smart Clinic Management System.

Handles tenant management, user administration, and super admin operations.
Extracted from routers/admin.py to follow service layer pattern.
"""

import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from backend import models
from backend.core.permissions import Role

logger = logging.getLogger(__name__)


class AdminService:
    """Service for admin and tenant management operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_all_tenants(self, skip: int = 0, limit: int = 100) -> List[models.Tenant]:
        """Get all tenants with pagination."""
        return self.db.query(models.Tenant).offset(skip).limit(limit).all()

    def get_tenant_by_id(self, tenant_id: int) -> Optional[models.Tenant]:
        """Get a single tenant by ID."""
        return (
            self.db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
        )

    def update_tenant(
        self,
        tenant_id: int,
        plan: str = None,
        is_active: bool = None,
        subscription_end_date: datetime = None,
    ) -> Optional[models.Tenant]:
        """Update tenant subscription details."""
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None

        if plan is not None:
            tenant.plan = plan
        if is_active is not None:
            tenant.is_active = is_active
        if subscription_end_date is not None:
            tenant.subscription_end_date = subscription_end_date

        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def archive_tenant(self, tenant_id: int) -> Optional[models.Tenant]:
        """Soft delete (archive) a tenant."""
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None

        tenant.is_deleted = True
        tenant.deleted_at = datetime.now(timezone.utc)
        tenant.is_active = False

        # Also deactivate the manager user
        manager = (
            self.db.query(models.User)
            .filter(
                models.User.tenant_id == tenant.id, models.User.role == Role.MANAGER.value
            )
            .first()
        )

        if manager:
            manager.is_deleted = True
            manager.is_active = False

        self.db.commit()
        return tenant

    def get_tenant_stats(self, tenant_id: int) -> Dict[str, Any]:
        """Get statistics for a specific tenant."""
        patient_count = (
            self.db.query(func.count(models.Patient.id))
            .filter(models.Patient.tenant_id == tenant_id)
            .scalar()
            or 0
        )

        user_count = (
            self.db.query(func.count(models.User.id))
            .filter(models.User.tenant_id == tenant_id, models.User.is_deleted == False)  # noqa: E712
            .scalar()
            or 0
        )

        return {
            "patients_count": patient_count,
            "users_count": user_count,
        }

    def get_users_for_tenant(self, tenant_id: int) -> List[models.User]:
        """Get all users belonging to a tenant."""
        return (
            self.db.query(models.User)
            .filter(models.User.tenant_id == tenant_id, models.User.is_deleted == False)  # noqa: E712
            .all()
        )

    def get_all_users(self, skip: int = 0, limit: int = 100) -> List[models.User]:
        """Get all users across all tenants (for super admin)."""
        return self.db.query(models.User).offset(skip).limit(limit).all()

    def deactivate_user(self, user_id: int) -> Optional[models.User]:
        """Deactivate a user account."""
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            return None

        user.is_active = False
        self.db.commit()
        return user

    def activate_user(self, user_id: int) -> Optional[models.User]:
        """Activate a user account."""
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            return None

        user.is_active = True
        self.db.commit()
        return user

    def restore_tenant(self, tenant_id: int) -> Optional[models.Tenant]:
        """Restore a soft-deleted tenant."""
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None

        tenant.is_deleted = False
        tenant.deleted_at = None
        tenant.is_active = True

        # Restore manager user
        manager = (
            self.db.query(models.User)
            .filter(
                models.User.tenant_id == tenant.id, models.User.role == Role.MANAGER.value
            )
            .first()
        )

        if manager:
            manager.is_deleted = False
            manager.is_active = True

        self.db.commit()
        return tenant

    def permanently_delete_tenant(self, tenant_id: int) -> bool:
        """
        Hard delete a tenant and all related data.
        WARNING: This is irreversible.

        Uses dynamic model discovery to find ALL tables with tenant_id,
        ensuring no FK constraints are missed even as new models are added.
        """
        from backend.models.base import Base

        try:
            tenant = self.get_tenant_by_id(tenant_id)
            if not tenant:
                return False

            # Dynamically find ALL models with tenant_id column
            tenant_models = []
            for mapper in Base.registry.mappers:
                model_class = mapper.class_
                if hasattr(model_class, "tenant_id") and model_class.__name__ != "Tenant":
                    tenant_models.append(model_class)

            # Also find models with user_id (for user-linked tables)
            user_models = []
            for mapper in Base.registry.mappers:
                model_class = mapper.class_
                if hasattr(model_class, "user_id") and not hasattr(model_class, "tenant_id"):
                    user_models.append(model_class)

            # Also find models with patient_id (for patient-linked tables)
            patient_models = []
            for mapper in Base.registry.mappers:
                model_class = mapper.class_
                if hasattr(model_class, "patient_id") and not hasattr(model_class, "tenant_id"):
                    patient_models.append(model_class)

            # 1. Get user IDs for this tenant
            user_ids = [
                u.id
                for u in self.db.query(models.User.id)
                .filter(models.User.tenant_id == tenant.id)
                .all()
            ]

            # 2. Get patient IDs for this tenant
            patient_ids = [
                p.id
                for p in self.db.query(models.Patient.id)
                .filter(models.Patient.tenant_id == tenant.id)
                .all()
            ]

            # 3. Delete from user-linked tables (no tenant_id)
            if user_ids:
                for model_class in user_models:
                    try:
                        with self.db.begin_nested():
                            self.db.query(model_class).filter(
                                model_class.user_id.in_(user_ids)
                            ).delete(synchronize_session=False)
                    except Exception as e:
                        logger.warning("Failed to clean %s (user): %s", model_class.__name__, e)

            # 4. Delete from patient-linked tables (no tenant_id)
            if patient_ids:
                for model_class in patient_models:
                    try:
                        with self.db.begin_nested():
                            self.db.query(model_class).filter(
                                model_class.patient_id.in_(patient_ids)
                            ).delete(synchronize_session=False)
                    except Exception as e:
                        logger.warning("Failed to clean %s (patient): %s", model_class.__name__, e)

            # 5. Delete ALL tenant-scoped tables (multiple passes for FK ordering)
            #    Repeat until no more deletions needed, handles any FK depth
            remaining = list(tenant_models)
            max_passes = 5
            for pass_num in range(max_passes):
                still_remaining = []
                for model_class in remaining:
                    try:
                        with self.db.begin_nested():
                            self.db.query(model_class).filter(
                                model_class.tenant_id == tenant.id
                            ).delete(synchronize_session=False)
                    except Exception as e:
                        still_remaining.append(model_class)
                        if pass_num == max_passes - 1:
                            logger.warning("Could not clean %s after %d passes: %s", model_class.__name__, max_passes, e)
                remaining = still_remaining
                if not remaining:
                    break

            # 6. Delete patients
            try:
                with self.db.begin_nested():
                    self.db.query(models.Patient).filter(
                        models.Patient.tenant_id == tenant.id
                    ).delete(synchronize_session=False)
            except Exception as e:
                logger.warning("Patient deletion error: %s", e)

            # 7. Delete users
            try:
                with self.db.begin_nested():
                    self.db.query(models.User).filter(
                        models.User.tenant_id == tenant.id
                    ).delete(synchronize_session=False)
            except Exception as e:
                logger.warning("User deletion error: %s", e)

            # 8. Finally, delete the tenant itself
            self.db.delete(tenant)
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.exception("[PERMANENT DELETE ERROR]", exc_info=True)
            raise e

