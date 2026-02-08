"""
Tenant Service

Business logic for tenant management, extracted from routers/admin.py.
Follows Clean Architecture: Router → Service → CRUD/Models
"""
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from backend import models, schemas
from backend.utils.audit_logger import log_admin_action
from backend.constants import ROLES


class TenantService:
    """Service layer for tenant management operations."""
    
    def __init__(self, db: Session, actor: models.User = None):
        """
        Initialize TenantService.
        
        Args:
            db: Database session
            actor: The user performing the action (for audit logging)
        """
        self.db = db
        self.actor = actor
    
    def get_tenant(self, tenant_id: int) -> Optional[models.Tenant]:
        """Get a tenant by ID."""
        return self.db.query(models.Tenant).filter(
            models.Tenant.id == tenant_id
        ).first()
    
    def get_all_tenants(self, skip: int = 0, limit: int = 100) -> list:
        """Get all tenants with pagination."""
        return self.db.query(models.Tenant).offset(skip).limit(limit).all()
    
    def update_tenant(
        self, 
        tenant_id: int, 
        update_data: schemas.TenantUpdate
    ) -> models.Tenant:
        """
        Update tenant subscription details.
        
        Business Rules:
        - Plan changes are logged for audit
        - is_active changes affect user login ability
        - subscription_end_date changes affect access expiry
        
        Raises:
            ValueError: If tenant not found
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")
        
        # Capture old values for audit
        old_values = {
            "plan": tenant.plan, 
            "is_active": tenant.is_active, 
            "end_date": str(tenant.subscription_end_date) if tenant.subscription_end_date else None
        }
        
        # Apply updates
        if update_data.plan is not None:
            tenant.plan = update_data.plan
        if update_data.is_active is not None:
            tenant.is_active = update_data.is_active
        if update_data.subscription_end_date is not None:
            tenant.subscription_end_date = update_data.subscription_end_date
        
        # Capture new values
        new_values = {
            "plan": tenant.plan, 
            "is_active": tenant.is_active, 
            "end_date": str(tenant.subscription_end_date) if tenant.subscription_end_date else None
        }
        
        # Audit log
        if self.actor:
            log_admin_action(
                self.db, self.actor, "update", "tenant", tenant.id,
                details="Updated tenant subscription",
                old_value=old_values, new_value=new_values
            )
        
        self.db.commit()
        self.db.refresh(tenant)
        return tenant
    
    def soft_delete_tenant(self, tenant_id: int) -> dict:
        """
        Soft delete (archive) a tenant.
        
        Business Rules:
        - Sets is_deleted = True
        - Records deleted_at timestamp
        - Deactivates tenant (is_active = False) to block login
        - Cascades soft delete to tenant's manager user
        
        Raises:
            ValueError: If tenant not found
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")
        
        # Soft delete tenant
        tenant.is_deleted = True
        tenant.deleted_at = datetime.utcnow()
        tenant.is_active = False  # Block login immediately
        
        # Cascade soft delete to manager/admin
        # Fix: Register triggers 'admin' role, not 'manager'
        admin_user = self.db.query(models.User).filter(
            models.User.tenant_id == tenant.id,
            models.User.role.in_([ROLES.ADMIN, ROLES.MANAGER]) 
        ).first()
        
        if admin_user:
            admin_user.is_deleted = True
            admin_user.is_active = False
        
        # Audit log
        if self.actor:
            log_admin_action(
                self.db, self.actor, "archive", "tenant", tenant.id,
                details=f"Archived tenant {tenant.name}"
            )
        
        self.db.commit()
        
        return {
            "message": "Tenant archived successfully",
            "tenant_id": tenant_id,
            "cascaded_users": 1 if admin_user else 0
        }
    
    def reactivate_tenant(self, tenant_id: int) -> models.Tenant:
        """
        Reactivate a soft-deleted tenant.
        
        Business Rules:
        - Clears is_deleted and deleted_at
        - Sets is_active = True
        - Does NOT automatically reactivate users (security)
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")
        
        tenant.is_deleted = False
        tenant.deleted_at = None
        tenant.is_active = True
        
        if self.actor:
            log_admin_action(
                self.db, self.actor, "reactivate", "tenant", tenant.id,
                details=f"Reactivated tenant {tenant.name}"
            )
        
        self.db.commit()
        self.db.refresh(tenant)
        return tenant
