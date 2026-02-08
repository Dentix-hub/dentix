from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend import models, schemas
from fastapi import HTTPException

class SubscriptionService:
    DEFAULT_GRACE_PERIOD_DAYS = 7

    @staticmethod
    def check_subscription_status(db: Session, tenant_id: int):
        """
        Evaluates the current status of a tenant subscription.
        Returns: 'active', 'grace_period', 'expired', 'suspended'
        """
        tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
        if not tenant:
            return None

        # 1. Check Forced Suspension
        # If manually set to inactive? The model has is_active.
        if not tenant.is_active:
            return "suspended"

        # 2. Check Expiry
        if not tenant.subscription_end_date:
            return "active"  # Assuming permanent/trial if no date? Or indefinite.

        now = datetime.utcnow()

        if now <= tenant.subscription_end_date:
            return "active"

        # 3. Check Grace Period
        grace_end = tenant.grace_period_until
        
        # If no custom grace period set, maybe we calculate default?
        # But let's assume grace_period_until is set explicitly or we use default logic if allowed.
        # For now, rely on DB field.
        if grace_end and now <= grace_end:
            return "grace_period"

        return "expired"

    @staticmethod
    def extend_grace_period(db: Session, tenant_id: int, days: int, reason: str):
        tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        tenant.grace_period_until = datetime.utcnow() + timedelta(days=days)
        tenant.manual_override_reason = reason
        # Ensure it's active if it was suspended due to expiry?
        # Usually we keep is_active=True but status is 'expired'.
        # If we want to allow login, we might need to ensure is_active is True.
        tenant.is_active = True 
        
        db.commit()
        return tenant

    @staticmethod
    def manual_suspend(db: Session, tenant_id: int, reason: str):
        tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        tenant.is_active = False
        tenant.manual_override_reason = f"Suspended: {reason}"
        db.commit()
        return tenant

    @staticmethod
    def get_subscription_details(db: Session, tenant_id: int):
        """Get full subscription details for UI/AI."""
        tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
        if not tenant:
            return None
        
        plan = None
        if tenant.plan_id: # Use plan_id as per new model, fallback to legacy if needed
            plan = db.query(models.SubscriptionPlan).filter(models.SubscriptionPlan.id == tenant.plan_id).first()
        
        # Fallback to string plan if plan_id is missing (Legacy support)
        plan_name = plan.display_name_ar if plan else (tenant.plan or "مجاني")
        plan_price = plan.price if plan else 0

        return {
            "plan_name": plan_name,
            "plan_price": plan_price,
            "status": tenant.subscription_status or "active",
            "start_date": None, # Add these fields to Tenant model if critical, currently legacy
            "end_date": str(tenant.subscription_end_date) if tenant.subscription_end_date else None,
            "is_active": tenant.subscription_status == "active"
        }

    @staticmethod
    def get_all_plans(db: Session):
        """List all active subscription plans."""
        return db.query(models.SubscriptionPlan).filter(models.SubscriptionPlan.is_active == True).all()

    @staticmethod
    def create_plan(db: Session, plan_data: schemas.SubscriptionPlanCreate):
        """Create a new subscription plan."""
        # Check if name exists
        existing = db.query(models.SubscriptionPlan).filter(models.SubscriptionPlan.name == plan_data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Plan with this name already exists")

        # Logic: If is_default is True, unset others
        if getattr(plan_data, "is_default", False):
            db.query(models.SubscriptionPlan).update({models.SubscriptionPlan.is_default: False})
            db.commit()
            
        new_plan = models.SubscriptionPlan(
            name=plan_data.name,
            display_name_ar=plan_data.display_name_ar,
            price=plan_data.price,
            duration_days=plan_data.duration_days,
            max_users=plan_data.max_users,
            max_patients=plan_data.max_patients,
            features=plan_data.features,
            is_ai_enabled=plan_data.is_ai_enabled,
            ai_daily_limit=plan_data.ai_daily_limit,
            ai_features=plan_data.ai_features,
            is_default=getattr(plan_data, "is_default", False),
            is_active=True
        )
        db.add(new_plan)
        db.commit()
        db.refresh(new_plan)
        return new_plan

    @staticmethod
    def update_plan(db: Session, plan_id: int, update_data: schemas.SubscriptionPlanUpdate):
        """Update an existing plan."""
        plan = db.query(models.SubscriptionPlan).filter(models.SubscriptionPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
            
        # Update fields dynamically
        update_dict = update_data.dict(exclude_unset=True)

        # Logic: If setting is_default=True, unset others
        if update_dict.get("is_default") is True:
             # Unset all other plans (excluding current)
             db.query(models.SubscriptionPlan).filter(models.SubscriptionPlan.id != plan_id).update({models.SubscriptionPlan.is_default: False})
             # Note: We don't commit here yet, as we will commit after updating the current plan

        for key, value in update_dict.items():
            setattr(plan, key, value)
            
        db.commit()
        db.refresh(plan)
        return plan

    @staticmethod
    def delete_plan(db: Session, plan_id: int):
        """Soft delete a plan (set is_active=False)."""
        plan = db.query(models.SubscriptionPlan).filter(models.SubscriptionPlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
            
        plan.is_active = False
        db.commit()
        return {"success": True, "message": "Plan deactivated successfully"}
