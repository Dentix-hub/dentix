import sys
import os

# Setup paths
sys.path.append(os.getcwd())

from backend.database import SessionLocal
from backend.models import User
from backend.services.auth_service import AuthService


def test_security_phase4():
    print("\n>>> Testing Phase 4: Advanced Security (Sessions & 2FA)...")
    db = SessionLocal()

    try:
        # 1. Setup Test User
        print("\n[1] Setting up Test User...")
        test_user = db.query(User).filter_by(username="phase4_user").first()
        if test_user:
            db.delete(test_user)
            db.commit()

        test_user = User(
            username="phase4_user", hashed_password="pw", is_2fa_enabled=False
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        print(f" - Created user: {test_user.username} (ID: {test_user.id})")

        # 2. Test Session Creation (Direct Service Call)
        print("\n[2] Testing Session Service...")
        import uuid

        session = AuthService.create_session(
            db, test_user.id, str(uuid.uuid4()), "127.0.0.1", "TestAgent"
        )
        if session and session.is_active:
            print(" - Session Created: PASS")
        else:
            print(" - Session Created: FAIL")

        # 3. Test Session Revocation
        print("\n[3] Testing Session Revocation...")
        revoked = AuthService.revoke_session(db, session.id, test_user.id)
        if revoked:
            print(" - Session Revoked: PASS")
        else:
            print(" - Session Revoked: FAIL")

        # 4. Test 2FA Setup
        print("\n[4] Testing 2FA Logic...")
        secret = AuthService.generate_2fa_secret(test_user)
        print(f" - Generated Secret: {secret}")

        # Enable 2FA
        # Using "123456" as our mock verified code from AuthService
        AuthService.enable_2fa(db, test_user, secret, "123456")

        if test_user.is_2fa_enabled and test_user.otp_secret == secret:
            print(" - 2FA Enabled: PASS")
        else:
            print(" - 2FA Enabled: FAIL")

        # 5. Verify 2FA Code Check
        valid = AuthService.verify_2fa_code(secret, "123456")
        invalid = AuthService.verify_2fa_code(secret, "000000")

        if valid and not invalid:
            print(" - OTP Verification Logic: PASS")
        else:
            print(" - OTP Verification Logic: FAIL")

    except Exception as e:
        print(f"!!! CRITICAL FAIL: {e}")
    finally:
        # Cleanup
        if "test_user" in locals() and test_user:
            db.delete(test_user)
            db.commit()
        db.close()


if __name__ == "__main__":
    test_security_phase4()
