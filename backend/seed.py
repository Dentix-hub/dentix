from sqlalchemy.orm import Session
import os
from . import models, auth

def seed_data(db: Session):
    """
    Seed database with initial data (Subscription Plans, Default Admin).
    Idempotent: checks for existing data before creating.
    """
    print("Running database seeding...")

    # 1. Subscription Plans
    default_plans = [
        {
            "name": "trial",
            "display_name_ar": "تجريبي",
            "price": 0.0,
            "duration_days": 14,
            "max_users": 1,
            "max_patients": 50,
            "features": "ملف مرضى محدود، تقارير أساسية",
            "is_active": True
        },
        {
            "name": "basic",
            "display_name_ar": "أساسي",
            "price": 29.99,
            "duration_days": 30,
            "max_users": 2,
            "max_patients": 500,
            "features": "ملفات مرضى، مواعيد، فواتير أساسية",
            "is_active": True
        },
        {
            "name": "pro",
            "display_name_ar": "محترف",
            "price": 79.99,
            "duration_days": 30,
            "max_users": 5,
            "max_patients": 2000,
            "features": "كل المزايا الأساسية + تقارير متقدمة + معمل",
            "is_active": True
        },
        {
            "name": "enterprise",
            "display_name_ar": "مؤسسات",
            "price": 199.99,
            "duration_days": 30,
            "max_users": None,
            "max_patients": None,
            "features": "كل شيء مفتوح + دعم فني مخصص",
            "is_active": True
        }
    ]

    plans_created = 0
    for plan_data in default_plans:
        existing_plan = db.query(models.SubscriptionPlan).filter(
            models.SubscriptionPlan.name == plan_data["name"]
        ).first()
        
        if not existing_plan:
            print(f"Creating plan: {plan_data['name']}")
            new_plan = models.SubscriptionPlan(**plan_data)
            db.add(new_plan)
            plans_created += 1
    
    if plans_created > 0:
        db.commit()
        print(f"Created {plans_created} subscription plans.")

    # 2. Default Super Admin User
    # CHECK FOR PRODUCTION ENVIRONMENT
    env = os.getenv("ENV", "development").lower()
    allow_seed = os.getenv("ALLOW_PRODUCTION_SEED", "false").lower() == "true"

    if env == "production" and not allow_seed:
        print("SEEDING SKIP: ENV=production and ALLOW_PRODUCTION_SEED!=true")
        return

    super_admin = db.query(models.User).filter(models.User.role == "super_admin").first()
    if not super_admin:
        print("No super_admin found. Creating default 'admin' user.")
        
        # Find or create a system tenant (first tenant or create new)
        system_tenant = db.query(models.Tenant).filter(models.Tenant.name == "System Admin").first()
        if not system_tenant:
            # Create system tenant
            print("Creating System Tenant")
            system_tenant = models.Tenant(
                name="System Admin",
                subscription_status="active",
                plan="enterprise",
                is_active=True
            )
            db.add(system_tenant)
            db.commit()
            db.refresh(system_tenant)
        
        # Check if admin username already exists
        existing_admin = db.query(models.User).filter(models.User.username == "admin").first()
        if not existing_admin:
            # SECURITY: DO NOT USE HARDCODED PASSWORDS IN PRODUCTION
            # Require environment variables for admin creation
            admin_user_env = os.getenv("ADMIN_USERNAME", "admin")
            admin_pass_env = os.getenv("ADMIN_PASSWORD")

            if not admin_pass_env:
                if env == "production":
                    print("CRITICAL: ADMIN_PASSWORD not set in production. Skipping admin creation.")
                    return
                else:
                    print("WARNING: ADMIN_PASSWORD not set. Using default dev password.")
                    admin_pass_env = "admin123"

            hashed_pwd = auth.get_password_hash(admin_pass_env)
            admin_user = models.User(
                username=admin_user_env,
                hashed_password=hashed_pwd,
                role="super_admin",
                tenant_id=system_tenant.id
            )
            db.add(admin_user)
            db.commit()
            print(f"Default super_admin created: username='{admin_user_env}'")
        else:
            print("Admin user already exists, skipping creation.")

    print("Seeding completed successfully.")

