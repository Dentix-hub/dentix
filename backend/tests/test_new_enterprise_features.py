import sys
import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

# Setup paths
sys.path.append(os.getcwd())

from backend.database import SessionLocal, Base, engine
from backend.models import User, FeatureFlag, TenantFeature, BlockedIP, LoginHistory, Tenant
from backend.services.security_service import SecurityService
from backend.services.feature_service import FeatureFlagService
from backend import schemas

def test_security_service(db):
    print("\n>>> Testing SecurityService...")
    # db fixture is passed in
    try:
        # 1. Test Block IP
        test_ip = "192.168.1.999"
        print(f"Blocking IP {test_ip}...")
        try:
            SecurityService.block_ip(db, test_ip, "Test Block", "admin", minutes=1)
            print(" - Blocked IP successfully.")
        except Exception as e:
            print(f" - Failed to block IP (might already exist): {e}")

        # Verify Block
        blocked = SecurityService.check_ip_blocked(db, test_ip)
        if blocked:
            print(" - check_ip_blocked: PASS (IP is blocked)")
        else:
            print(" - check_ip_blocked: FAIL (IP not found)")

        # Unblock
        print("Unblocking IP...")
        SecurityService.unblock_ip(db, test_ip)
        blocked = SecurityService.check_ip_blocked(db, test_ip)
        if not blocked:
            print(" - unblock_ip: PASS")
        else:
            print(" - unblock_ip: FAIL")

        # 2. Test Login Attempts
        print("Testing Login Attempts...")
        # Clean up previous run artifacts
        existing_user = db.query(User).filter_by(username="security_test_user").first()
        if existing_user:
            db.delete(existing_user)
            db.commit()

        # Create a temp user
        temp_user = User(username="security_test_user", hashed_password="pw")
        db.add(temp_user)
        db.commit()
        
        # Fail 5 times
        for i in range(5):
            SecurityService.record_login_attempt(db, "127.0.0.1", temp_user.username, False, temp_user)
        
        db.refresh(temp_user)
        print(f"Failed attempts: {temp_user.failed_login_attempts}")
        
        if SecurityService.is_account_locked(temp_user):
            print(" - Account Locking: PASS (User is locked)")
        else:
            print(" - Account Locking: FAIL (User should be locked)")
            
        # Cleanup
        db.delete(temp_user)
        db.commit()

    finally:
        pass # Fixture handles closing

def test_feature_flags(db):
    print("\n>>> Testing FeatureFlags...")
    # db fixture passed in
    try:
        # 1. Create Flag
        key = "test_feature_ai"
        print(f"Creating flag '{key}'...")
        
        # Cleanup first
        existing = db.query(FeatureFlag).filter_by(key=key).first()
        if existing:
            db.delete(existing)
            db.commit()

        flag_data = schemas.FeatureFlagCreate(
            key=key,
            description="Test AI",
            is_global_enabled=False,
            rollout_percentage=0
        )
        FeatureFlagService.create_flag(db, flag_data)
        
        # Check Default (Should be False)
        if not FeatureFlagService.is_feature_enabled(db, key):
             print(" - Default Disabled: PASS")
        else:
             print(" - Default Disabled: FAIL")

        # 2. Enable Global
        print("Enabling globally...")
        FeatureFlagService.update_flag(db, key, {"is_global_enabled": True})
        if FeatureFlagService.is_feature_enabled(db, key):
             print(" - Global Enable: PASS")
        else:
             print(" - Global Enable: FAIL")

        # 3. Test Tenant Override
        print("Testing Tenant Override (Disable for tenant 999)...")
        # We don't need real tenant table for logic check if FK constraints don't block us?
        # FK constraints might block us if tenant_id 999 doesn't exist.
        # Let's check logic implies we insert into TenantFeature.
        # We need a valid tenant ID.
        tenant = db.query(Tenant).first()
        if tenant:
            t_id = tenant.id
            FeatureFlagService.set_tenant_override(db, t_id, key, False)
            
            is_enabled = FeatureFlagService.is_feature_enabled(db, key, t_id)
            if not is_enabled:
                print(f" - Tenant Override (Disable): PASS for tenant {t_id}")
            else:
                print(f" - Tenant Override (Disable): FAIL for tenant {t_id}")
                
            # Clean override
            db.query(TenantFeature).filter_by(tenant_id=t_id, feature_key=key).delete()
            db.commit()
        else:
            print(" - SKIP: No tenants found to test overrides.")

        # Cleanup Flag
        db.query(FeatureFlag).filter_by(key=key).delete()
        db.commit()

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        pass

if __name__ == "__main__":
    test_security_service()
    test_feature_flags()
