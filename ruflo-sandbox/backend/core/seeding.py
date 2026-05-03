import logging
logger = logging.getLogger(__name__)
import os
from sqlalchemy.exc import OperationalError
from backend import database, models
from backend import auth


def create_first_admin():
    """Ensure default admin exists for first-time setup."""
    db = database.SessionLocal()
    try:
        super_email = os.getenv('SUPER_ADMIN_EMAIL')
        super_pass = os.getenv('SUPER_ADMIN_PASSWORD')
        if not super_email or not super_pass:
            logger.info(
                '[SEED] SUPER_ADMIN_EMAIL or SUPER_ADMIN_PASSWORD not set. Skipping super admin creation.'
                )
            return
        super_admin = db.query(models.User).filter(models.User.username ==
            super_email).first()
        if not super_admin:
            new_super = models.User(username=super_email, hashed_password=
                auth.get_password_hash(super_pass), role='super_admin',
                tenant_id=None)
            db.add(new_super)
            db.commit()
    finally:
        db.close()


def seed_subscription_plans():
    """
    Seed default subscription plans.
    Idempotent and safe: checks if table exists and plans are missing.
    """
    db = database.SessionLocal()
    try:
        if not db.query(models.SubscriptionPlan).first():
            logger.info(
                '[SEED] No subscription plans found. Seeding defaults...')
            plans = [models.SubscriptionPlan(name='trial', display_name_ar=
                'تجريبي', price=0, duration_days=7, features='مجاني ٧ أيام',
                max_users=1, max_patients=10), models.SubscriptionPlan(name
                ='basic', display_name_ar='أساسي', price=500, duration_days
                =30, features='١ مستخدم، ١٠٠ مريض', max_users=1,
                max_patients=100), models.SubscriptionPlan(name='pro',
                display_name_ar='محترف', price=1000, duration_days=30,
                features='٥ مستخدمين، مرضى غير محدود', max_users=5,
                max_patients=None), models.SubscriptionPlan(name=
                'enterprise', display_name_ar='مؤسسات', price=2500,
                duration_days=30, features='غير محدود', max_users=None,
                max_patients=None)]
            db.add_all(plans)
            db.commit()
            logger.info('[SEED] Subscription plans seeded successfully.')
        else:
            logger.info('[SEED] Subscription plans already exist. Skipping.')
    except OperationalError:
        logger.info(
            "[WARNING] Could not seed subscription plans: Table 'subscription_plans' does not exist yet."
            )
    except Exception as e:
        logger.info(f'[ERROR] Failed to seed subscription plans: {e}')
    finally:
        db.close()


def manual_seed_database_logic():
    """Logic for manual seed endpoint."""
    try:
        from backend.scripts.seeds import seed
        db = database.SessionLocal()
        seed.seed_data(db)
        db.close()
        return {'message': 'Database seeding completed successfully'}
    except Exception as e:
        return {'error': str(e)}
