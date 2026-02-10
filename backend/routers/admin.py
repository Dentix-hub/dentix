from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List
from datetime import datetime
from datetime import timezone
import traceback

from .. import models, schemas
from .auth import get_current_user, get_db
from ..utils.audit_logger import log_admin_action
from ..constants import ROLES

print("LOADING ADMIN ROUTER")
router = APIRouter(tags=["Super Admin"])


def require_super_admin(current_user: models.User = Depends(get_current_user)):
    """Verify user is super admin."""
    if current_user.role != ROLES.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user


# --- Tenant Management ---
@router.get("/tenants", response_model=List[schemas.Tenant])
def get_all_tenants(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Get all tenants (super admin only)."""
    try:
        return db.query(models.Tenant).offset(skip).limit(limit).all()
    except Exception as e:
        print(f"[ADMIN ERROR] {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Tenant Fetch Error: {str(e)}")


@router.put("/tenants/{tenant_id}", response_model=schemas.Tenant)
def update_tenant(
    tenant_id: int,
    tenant_update: schemas.TenantUpdate,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Update tenant subscription."""
    try:
        tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        old_values = {
            "plan": tenant.plan,
            "is_active": tenant.is_active,
            "end_date": tenant.subscription_end_date,
        }

        if tenant_update.plan is not None:
            tenant.plan = tenant_update.plan
        if tenant_update.is_active is not None:
            tenant.is_active = tenant_update.is_active
        if tenant_update.subscription_end_date is not None:
            tenant.subscription_end_date = tenant_update.subscription_end_date

        new_values = {
            "plan": tenant.plan,
            "is_active": tenant.is_active,
            "end_date": tenant.subscription_end_date,
        }

        log_admin_action(
            db,
            current_user,
            "update",
            "tenant",
            tenant.id,
            details="Updated tenant subscription",
            old_value=old_values,
            new_value=new_values,
        )

        db.commit()
        db.refresh(tenant)
        return tenant
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update Tenant Error: {str(e)}")


@router.delete("/tenants/{tenant_id}")
def delete_tenant(
    tenant_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Archive (Soft Delete) tenant."""
    try:
        tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        tenant.is_deleted = True
        tenant.deleted_at = datetime.now(timezone.utc)
        tenant.is_active = False  # Deactivate login instantly

        # Soft delete admin user as well for safety
        admin_user = (
            db.query(models.User)
            .filter(
                models.User.tenant_id == tenant.id, models.User.role == ROLES.MANAGER
            )
            .first()
        )
        if admin_user:
            admin_user.is_deleted = True
            admin_user.is_active = False

        log_admin_action(
            db,
            current_user,
            "archive",
            "tenant",
            tenant.id,
            details=f"Archived tenant {tenant.name}",
        )

        db.commit()
        return {"message": "Tenant archived successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to archive tenant: {str(e)}"
        )


@router.post("/tenants/{tenant_id}/restore")
def restore_tenant(
    tenant_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Restore archived tenant."""
    try:
        tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        tenant.is_deleted = False
        tenant.deleted_at = None
        tenant.is_active = True

        admin_user = (
            db.query(models.User)
            .filter(
                models.User.tenant_id == tenant.id, models.User.role == ROLES.MANAGER
            )
            .first()
        )
        if admin_user:
            admin_user.is_deleted = False
            admin_user.is_active = True

        log_admin_action(
            db,
            current_user,
            "restore",
            "tenant",
            tenant.id,
            details=f"Restored tenant {tenant.name}",
        )

        db.commit()
        return {"message": "Tenant restored successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore Tenant Error: {str(e)}")


@router.delete("/tenants/{tenant_id}/permanent")
def delete_tenant_permanently(
    tenant_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Permanently delete a tenant and all associated data."""
    try:
        tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # Log action before deletion
        try:
            log_admin_action(
                db,
                current_user,
                "delete_permanent",
                "tenant",
                tenant.id,
                details=f"Permanently deleting tenant {tenant.name} ({tenant_id}) and ALL associated data",
            )
            # CRITICAL: Commit the log so the transaction is clean for the deletion steps.
            # If we don't commit, a flush failure during delete will abort the transaction.
            db.commit()
        except Exception as log_error:
            # If logging fails, just print it and continue (don't block deletion)
            print(f"[WARN] Failed to log delete action: {log_error}")
            db.rollback()  # Rollback the log attempt

        # Use a fresh connection/session approach to avoid transaction issues
        # Process each major group separately to prevent transaction corruption

        # 1. Handle user-related tables first
        try:
            user_ids = [
                u.id
                for u in db.query(models.User.id)
                .filter(models.User.tenant_id == tenant.id)
                .all()
            ]
            if user_ids:
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
                                with db.begin_nested():
                                    count = (
                                        db.query(table_model)
                                        .filter(table_model.user_id.in_(user_ids))
                                        .delete(synchronize_session=False)
                                    )
                                    print(f"Deleted {count} {table_attr} records")
                        except Exception as e:
                            print(f"[WARN] Failed to clean {table_attr}: {e}")
                            # Continue despite error
        except Exception as e:
            print(f"[WARN] User-related cleanup error: {e}")
            # Continue despite error

        # 2. Handle patient-related tables
        try:
            patient_ids = [
                p.id
                for p in db.query(models.Patient.id)
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
                                with db.begin_nested():
                                    count = (
                                        db.query(table_model)
                                        .filter(table_model.patient_id.in_(patient_ids))
                                        .delete(synchronize_session=False)
                                    )
                                    print(f"Deleted {count} {table_attr} records")
                        except Exception as e:
                            print(f"[WARN] Failed to clean {table_attr}: {e}")
                            # Continue despite error
        except Exception as e:
            print(f"[WARN] Patient-related cleanup error: {e}")
            # Continue despite error

        # 3. Handle tenant-specific tables with more robust error handling
        tenant_specific_tables = [
            (models.SubscriptionPayment, "SubscriptionPayment"),
            (models.Expense, "Expense"),
            (models.SalaryPayment, "SalaryPayment"),
            (models.Payment, "Payment"),
            (models.Laboratory, "Laboratory"),
            (models.Procedure, "Procedure"),
            (models.AIUsageLog, "AIUsageLog"),
            (models.SupportMessage, "SupportMessage"),
            (models.BackgroundJob, "BackgroundJob"),
            (models.TenantFeature, "TenantFeature"),
            (models.Notification, "Notification"),
            (models.AuditLog, "AuditLog"),
        ]

        for table_model, table_name in tenant_specific_tables:
            try:
                if hasattr(table_model, "tenant_id"):
                    with db.begin_nested():
                        count = (
                            db.query(table_model)
                            .filter(table_model.tenant_id == tenant.id)
                            .delete(synchronize_session=False)
                        )
                        print(f"Deleted {count} {table_name} records")
            except Exception as e:
                print(f"[WARN] Failed to clean {table_name}: {e}")
                # Continue despite error

        # 4. Handle patients
        try:
            with db.begin_nested():
                patients = (
                    db.query(models.Patient)
                    .filter(models.Patient.tenant_id == tenant.id)
                    .all()
                )
                for patient in patients:
                    try:
                        with db.begin_nested():
                            # Delete attachments for this patient if they weren't handled above
                            if hasattr(models, "Attachment"):
                                db.query(models.Attachment).filter(
                                    models.Attachment.patient_id == patient.id
                                ).delete(synchronize_session=False)

                            db.delete(patient)
                    except Exception as inner_e:
                        print(
                            f"[WARN] Failed to delete patient {patient.id}: {inner_e}"
                        )
                print(f"Deleted {len(patients)} patients")
        except Exception as e:
            print(f"[WARN] Patient deletion error: {e}")
            # Continue despite error

        # 5. Handle users
        try:
            with db.begin_nested():
                user_count = (
                    db.query(models.User)
                    .filter(models.User.tenant_id == tenant.id)
                    .delete(synchronize_session=False)
                )
                print(f"Deleted {user_count} users")
        except Exception as e:
            print(f"[WARN] User deletion error: {e}")
            # Continue despite error

        # 6. Finally, delete the tenant itself
        try:
            with db.begin_nested():
                db.delete(tenant)
                print(f"Deleted tenant {tenant.name} (ID: {tenant.id})")
        except Exception as e:
            print(f"[WARN] Failed to delete tenant: {e}")
            raise  # Re-raise for main exception handler

        db.commit()
        return {
            "message": f"Tenant {tenant.name} and all associated data permanently deleted."
        }

    except Exception as e:
        db.rollback()
        import traceback

        tb = traceback.format_exc()
        print(f"[PERMANENT DELETE ERROR] {tb}")
        # Return exact error for debugging
        # Return exact error for debugging
        raise HTTPException(
            status_code=500,
            detail=f"Permanent Delete Error: {str(e)} | Details: {tb.splitlines()[-1]}",
        )


@router.delete("/tenants/{tenant_id}/purge-deleted-patients")
def purge_soft_deleted_patients(
    tenant_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Permanently delete ALL patients marked as soft-deleted for a specific tenant.
    Tenant admins can only purge their own tenant's data.
    """
    # Allow super_admin OR admin of the same tenant
    if current_user.role != "super_admin" and (
        current_user.role != "admin" or current_user.tenant_id != tenant_id
    ):
        raise HTTPException(
            status_code=403, detail="Not authorized to purge this tenant's data"
        )

    try:
        # Find all soft-deleted patients for this tenant
        deleted_patients = (
            db.query(models.Patient)
            .filter(
                models.Patient.tenant_id == tenant_id, models.Patient.is_deleted == True
            )
            .all()
        )

        count = len(deleted_patients)
        if count == 0:
            return {"message": "No soft-deleted patients found to purge."}

        success_count = 0
        from .. import crud

        for patient in deleted_patients:
            try:
                # Reuse the hard delete logic
                crud.delete_patient_permanently(db, patient.id, tenant_id)
                success_count += 1
            except Exception as e:
                print(f"[PURGE ERROR] Failed to purge patient {patient.id}: {e}")

        # Log the bulk action
        log_admin_action(
            db,
            current_user,
            "purge",
            "patient",
            0,
            details=f"Purged {success_count} soft-deleted patients for tenant {tenant_id}",
        )

        return {
            "message": f"Purge complete. Permanently deleted {success_count} patients.",
            "total_found": count,
            "success_count": success_count,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Purge Error: {str(e)}")


@router.post("/tenants/{tenant_id}/assign-plan")
def assign_plan_to_tenant(
    tenant_id: int,
    plan_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Assign a subscription plan to a tenant."""
    try:
        from datetime import timedelta

        tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        plan = (
            db.query(models.SubscriptionPlan)
            .filter(models.SubscriptionPlan.id == plan_id)
            .first()
        )
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        # Update tenant
        tenant.plan = plan.name
        tenant.plan_id = plan.id
        tenant.is_active = True
        tenant.subscription_end_date = datetime.now(timezone.utc) + timedelta(
            days=plan.duration_days
        )

        db.commit()
        db.refresh(tenant)
        return {
            "message": f"Plan '{plan.name}' assigned successfully",
            "tenant": tenant.name,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assign Plan Error: {str(e)}")


# --- Subscription Plans ---
@router.get("/plans", response_model=List[schemas.SubscriptionPlan])
def get_subscription_plans(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Get all subscription plans."""
    try:
        plans = (
            db.query(models.SubscriptionPlan)
            .filter(models.SubscriptionPlan.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )
        print(f"[DEBUG] Fetching active plans. Count: {len(plans)}", flush=True)
        return plans
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fetch Plans Error: {str(e)}")


@router.post("/plans", response_model=schemas.SubscriptionPlan)
def create_subscription_plan(
    plan: schemas.SubscriptionPlanCreate,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Create new subscription plan."""
    try:
        db_plan = models.SubscriptionPlan(**plan.model_dump())
        db.add(db_plan)
        db.commit()
        db.refresh(db_plan)

        log_admin_action(
            db,
            current_user,
            "create",
            "plan",
            db_plan.id,
            details=f"Created plan {db_plan.name}",
            new_value=plan.model_dump(),
        )

        return db_plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Create Plan Error: {str(e)}")


@router.put("/plans/{plan_id}", response_model=schemas.SubscriptionPlan)
def update_subscription_plan(
    plan_id: int,
    plan_update: schemas.SubscriptionPlanUpdate,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Update subscription plan."""
    try:
        plan = (
            db.query(models.SubscriptionPlan)
            .filter(models.SubscriptionPlan.id == plan_id)
            .first()
        )
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        for key, value in plan_update.model_dump(exclude_unset=True).items():
            setattr(plan, key, value)

        db.commit()
        db.refresh(plan)
        return plan
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update Plan Error: {str(e)}")


# --- Subscription Payments ---
@router.get("/payments", response_model=List[schemas.SubscriptionPayment])
def get_subscription_payments(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Get all subscription payments."""
    try:
        return (
            db.query(models.SubscriptionPayment)
            .order_by(models.SubscriptionPayment.payment_date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fetch Payments Error: {str(e)}")


@router.post("/payments", response_model=schemas.SubscriptionPayment)
def record_subscription_payment(
    payment: schemas.SubscriptionPaymentCreate,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Record subscription payment."""
    try:
        tenant = (
            db.query(models.Tenant)
            .filter(models.Tenant.id == payment.tenant_id)
            .first()
        )
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        plan = (
            db.query(models.SubscriptionPlan)
            .filter(models.SubscriptionPlan.id == payment.plan_id)
            .first()
        )
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        # Create payment record
        db_payment = models.SubscriptionPayment(
            **payment.model_dump(exclude={"payment_date"}),
            payment_date=payment.payment_date or datetime.now(timezone.utc),
            created_by=current_user.username,
        )
        db.add(db_payment)

        # Update tenant subscription
        target_date = (
            tenant.subscription_end_date
            if tenant.subscription_end_date
            and tenant.subscription_end_date > datetime.now(timezone.utc)
            else datetime.now(timezone.utc)
        )
        from datetime import timedelta

        tenant.subscription_end_date = target_date + timedelta(days=plan.duration_days)

        tenant.plan = plan.name
        tenant.is_active = True

        db.commit()
        db.refresh(db_payment)

        log_admin_action(
            db,
            current_user,
            "create",
            "payment",
            db_payment.id,
            details=f"Recorded payment of {db_payment.amount} for {tenant.name}",
            new_value={"amount": payment.amount, "plan": plan.name},
        )

        return db_payment
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Record Payment Error: {str(e)}")


@router.delete("/payments/{payment_id}")
def delete_subscription_payment(
    payment_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Delete subscription payment."""
    try:
        payment = (
            db.query(models.SubscriptionPayment)
            .filter(models.SubscriptionPayment.id == payment_id)
            .first()
        )
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        # Log action before deletion
        log_admin_action(
            db,
            current_user,
            "delete",
            "payment",
            payment.id,
            details=f"Deleted payment of {payment.amount} for tenant ID {payment.tenant_id}",
            old_value={"amount": payment.amount, "plan_id": payment.plan_id},
        )
        # Commit log
        db.commit()

        db.delete(payment)
        db.commit()

        return {"message": "Payment deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Delete Payment Error: {str(e)}")


# --- Dashboard Stats ---
@router.get("/stats", response_model=schemas.AdminDashboardStats)
def get_admin_dashboard_stats(
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Get admin dashboard statistics."""
    try:
        total_tenants = db.query(models.Tenant).count()
        active_tenants = (
            db.query(models.Tenant).filter(models.Tenant.is_active == True).count()
        )
        expired_tenants = (
            db.query(models.Tenant)
            .filter(models.Tenant.subscription_end_date < datetime.now(timezone.utc))
            .count()
        )

        total_revenue = (
            db.query(func.sum(models.SubscriptionPayment.amount)).scalar() or 0
        )

        # Monthly revenue (last 12 months)
        monthly_revenue = {}

        # Recent payments
        recent_payments = (
            db.query(models.SubscriptionPayment)
            .order_by(models.SubscriptionPayment.payment_date.desc())
            .limit(10)
            .all()
        )

        # Plan distribution
        plan_distribution = {}
        plans = (
            db.query(models.Tenant.plan, func.count(models.Tenant.id))
            .group_by(models.Tenant.plan)
            .all()
        )
        for plan_name, count in plans:
            plan_distribution[plan_name or "trial"] = count

        return {
            "total_tenants": total_tenants,
            "active_tenants": active_tenants,
            "expired_tenants": expired_tenants,
            "total_revenue": float(total_revenue),
            "monthly_revenue": monthly_revenue,
            "plan_distribution": plan_distribution,
            "recent_payments": recent_payments,
        }
    except Exception as e:
        import traceback

        print(f"[ADMIN STATS ERROR] {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Stats Error: {str(e)}")


# --- Audit Logs ---
@router.get("/audit-logs", response_model=List[schemas.AuditLog])
def get_audit_logs(
    skip: int = 0,
    limit: int = 50,
    tenant_id: int = None,
    user_id: int = None,
    action: str = None,
    start_date: str = None,
    end_date: str = None,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Get system audit logs with optional filters."""
    try:
        query = db.query(models.AuditLog)

        # Apply filters
        if tenant_id:
            query = query.filter(models.AuditLog.tenant_id == tenant_id)
        if user_id:
            query = query.filter(models.AuditLog.performed_by_id == user_id)
        if action:
            query = query.filter(models.AuditLog.action == action)
        if start_date:
            from datetime import datetime

            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                query = query.filter(models.AuditLog.created_at >= start_dt)
            except ValueError:
                pass
        if end_date:
            from datetime import datetime, timedelta

            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
                query = query.filter(models.AuditLog.created_at < end_dt)
            except ValueError:
                pass

        return (
            query.order_by(models.AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit Logs Error: {str(e)}")


# --- User Management (Global) ---
@router.get("/users", response_model=List[schemas.UserAdminView])
def get_global_users(
    search_query: str = None,
    role: str = None,
    skip: int = 0,
    limit: int = 50,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Search and manage global users."""
    query = (
        db.query(models.User)
        .filter(models.User.is_deleted == False)
        .options(joinedload(models.User.tenant))
    )

    if search_query:
        search = f"%{search_query}%"
        # Join with Tenant to search by clinic name too if needed,
        # but User model has is_deleted=False filter.
        query = query.join(models.Tenant, isouter=True).filter(
            (models.User.username.ilike(search))
            | (models.User.email.ilike(search))
            | (models.Tenant.name.ilike(search))
        )

    if role and role != "all":
        query = query.filter(models.User.role == role)

    users = query.offset(skip).limit(limit).all()

    # Enrich with tenant name manually if not eager loaded or use Pydantic logic
    # The Schema expects tenant_name.
    result = []
    for u in users:
        u_schema = schemas.UserAdminView.model_validate(u)
        if u.tenant:
            u_schema.tenant_name = u.tenant.name
        else:
            u_schema.tenant_name = "System / No Clinic"  # e.g. super admin
        result.append(u_schema)

    return result


@router.post("/users/{user_id}/toggle-status")
def toggle_user_status(
    user_id: int,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Enable/Disable user account."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent disabling self
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot disable your own account")

    new_status = not user.is_active
    user.is_active = new_status

    log_admin_action(
        db,
        current_user,
        "update",
        "user",
        user.id,
        details=f"{'Enabled' if new_status else 'Disabled'} user {user.username}",
        target_user_id=user.id,
        new_value={"is_active": new_status},
    )

    db.commit()
    return {
        "message": f"User {'enabled' if new_status else 'disabled'} successfully",
        "is_active": new_status,
    }


# --- Global System Settings (Phase 3) ---
@router.get("/settings", response_model=List[schemas.SystemSetting])
def get_system_settings(
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Get all global system settings."""
    return db.query(models.SystemSetting).all()


@router.put("/settings/{key}", response_model=schemas.SystemSetting)
def update_system_setting(
    key: str,
    setting_update: schemas.SystemSetting,  # using same schema for input, though ideally separate
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Update a system setting."""
    setting = (
        db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
    )
    if not setting:
        # Create if not exists (Upsert)
        setting = models.SystemSetting(key=key, value=setting_update.value)
        db.add(setting)
        db.commit()
        db.refresh(setting)

        log_admin_action(
            db,
            current_user,
            "create",
            "setting",
            0,
            details=f"Created setting {key}",
            new_value={key: setting.value},
        )
        return setting

    old_value = setting.value
    setting.value = setting_update.value
    # setting.description = setting_update.description # keep desc static usually

    log_admin_action(
        db,
        current_user,
        "update",
        "setting",
        0,  # Use 0 or hash for ID
        details=f"Updated setting {key}",
        old_value={key: old_value},
        new_value={key: setting.value},
    )

    db.commit()
    db.refresh(setting)
    return setting


@router.get("/system/google/auth-url")
def get_system_google_auth_url(
    current_user: models.User = Depends(require_super_admin),
):
    """
    Get Google Drive Auth URL for System Backups (Super Admin).
    Passes state='super_admin' so the callback knows to save to SystemSettings.
    """
    from ..main import drive_client

    auth_url = drive_client.get_auth_url(state="super_admin")
    return {"url": auth_url}
