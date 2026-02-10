"""
Admin Service for Smart Clinic Management System.

Handles tenant management, user administration, and super admin operations.
Extracted from routers/admin.py to follow service layer pattern.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import List, Dict, Any, Optional

from backend import models
from backend.constants import ROLES


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
        tenant.deleted_at = datetime.utcnow()
        tenant.is_active = False

        # Also deactivate the manager user
        manager = (
            self.db.query(models.User)
            .filter(
                models.User.tenant_id == tenant.id, models.User.role == ROLES.MANAGER
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
            .filter(models.User.tenant_id == tenant_id, models.User.is_deleted == False)
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
            .filter(models.User.tenant_id == tenant_id, models.User.is_deleted == False)
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
                models.User.tenant_id == tenant.id, models.User.role == ROLES.MANAGER
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
        """
        try:
            tenant = self.get_tenant_by_id(tenant_id)
            if not tenant:
                return False

            # 1. Handle user-related tables first
            try:
                user_ids = [
                    u.id
                    for u in self.db.query(models.User.id)
                    .filter(models.User.tenant_id == tenant.id)
                    .all()
                ]
                if user_ids:
                    # Generic cleanup for user-linked tables
                    for table_attr in [
                        "PasswordResetToken",
                        "NotificationRead",
                        "UserSession",
                        "LoginHistory",
                    ]:
                        if hasattr(models, table_attr):
                            table_model = getattr(models, table_attr)
                            try:
                                if hasattr(table_model, "user_id"):
                                    with self.db.begin_nested():
                                        self.db.query(table_model).filter(
                                            table_model.user_id.in_(user_ids)
                                        ).delete(synchronize_session=False)
                            except Exception:
                                pass
            except Exception as e:
                print(f"[WARN] User-related cleanup error: {e}")

            # 2. Handle patient-related tables
            try:
                patient_ids = [
                    p.id
                    for p in self.db.query(models.Patient.id)
                    .filter(models.Patient.tenant_id == tenant.id)
                    .all()
                ]
                if patient_ids:
                    for table_attr in [
                        "Appointment",
                        "Prescription",
                        "LabOrder",
                        "Treatment",
                        "Attachment",
                        "ToothStatus",
                    ]:
                        if hasattr(models, table_attr):
                            table_model = getattr(models, table_attr)
                            try:
                                if hasattr(table_model, "patient_id"):
                                    with self.db.begin_nested():
                                        self.db.query(table_model).filter(
                                            table_model.patient_id.in_(patient_ids)
                                        ).delete(synchronize_session=False)
                            except Exception:
                                pass
            except Exception as e:
                print(f"[WARN] Patient-related cleanup error: {e}")

            # 3. Handle tenant-specific tables
            tenant_specific_tables = [
                "SubscriptionPayment",
                "Expense",
                "SalaryPayment",
                "Payment",
                "Laboratory",
                "Procedure",
                "AIUsageLog",
                "SupportMessage",
                "BackgroundJob",
                "TenantFeature",
                "Notification",
                "AuditLog",
            ]

            for table_name in tenant_specific_tables:
                if hasattr(models, table_name):
                    table_model = getattr(models, table_name)
                    try:
                        if hasattr(table_model, "tenant_id"):
                            with self.db.begin_nested():
                                self.db.query(table_model).filter(
                                    table_model.tenant_id == tenant.id
                                ).delete(synchronize_session=False)
                    except Exception as e:
                        print(f"[WARN] Failed to clean {table_name}: {e}")

            # 4. Handle patients
            try:
                with self.db.begin_nested():
                    self.db.query(models.Patient).filter(
                        models.Patient.tenant_id == tenant.id
                    ).delete(synchronize_session=False)
            except Exception as e:
                print(f"[WARN] Patient deletion error: {e}")

            # 5. Handle users
            try:
                with self.db.begin_nested():
                    self.db.query(models.User).filter(
                        models.User.tenant_id == tenant.id
                    ).delete(synchronize_session=False)
            except Exception as e:
                print(f"[WARN] User deletion error: {e}")

            # 6. Finally, delete the tenant itself
            self.db.delete(tenant)
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            print(f"[PERMANENT DELETE ERROR] {e}")
            raise e
