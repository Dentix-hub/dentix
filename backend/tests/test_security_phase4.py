import sys
import os
import pytest
from sqlalchemy import select
import uuid
import pyotp

# Setup paths
sys.path.append(os.getcwd())

from backend.models import User
from backend.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_security_phase4(async_db_session):
    print("\n>>> Testing Phase 4: Advanced Security (Sessions & 2FA)...")
    db = async_db_session

    try:
        # 1. Setup Test User
        print("\n[1] Setting up Test User...")
        stmt = select(User).filter_by(username="phase4_user")
        res = await db.execute(stmt)
        test_user = res.scalars().first()
        if test_user:
            await db.delete(test_user)
            await db.commit()

        test_user = User(
            username="phase4_user",
            email="phase4_user@example.com",
            hashed_password="pw",
            is_2fa_enabled=False,
        )
        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)
        print(f" - Created user: {test_user.username} (ID: {test_user.id})")

        # 2. Test Session Creation (Direct Service Call)
        print("\n[2] Testing Session Service...")
        session = await AuthService.create_session(
            db, test_user.id, str(uuid.uuid4()), "127.0.0.1", "TestAgent"
        )
        if session and session.is_active:
            print(" - Session Created: PASS")
        else:
            print(" - Session Created: FAIL")
            assert False, "Session creation failed"

        # 3. Test Session Revocation
        print("\n[3] Testing Session Revocation...")
        revoked = await AuthService.revoke_session(db, session.id, test_user.id)
        if revoked:
            print(" - Session Revoked: PASS")
        else:
            print(" - Session Revoked: FAIL")
            assert False, "Session revocation failed"

        # 4. Test 2FA Setup
        print("\n[4] Testing 2FA Logic...")
        secret = AuthService.generate_2fa_secret(test_user)
        valid_code = pyotp.TOTP(secret).now()

        # Enable 2FA
        await AuthService.enable_2fa(db, test_user, secret, valid_code)

        if test_user.is_2fa_enabled and test_user.otp_secret == secret:
            print(" - 2FA Enabled: PASS")
        else:
            print(" - 2FA Enabled: FAIL")
            assert False, "2FA enabling failed"

        # 5. Verify 2FA Code Check
        valid = AuthService.verify_2fa_code(secret, valid_code)
        invalid = AuthService.verify_2fa_code(secret, "000000")

        if valid and not invalid:
            print(" - OTP Verification Logic: PASS")
        else:
            print(" - OTP Verification Logic: FAIL")
            assert False, "2FA validation failed"

    finally:
        # Cleanup
        try:
            stmt = select(User).filter_by(username="phase4_user")
            res = await db.execute(stmt)
            u = res.scalars().first()
            if u:
                await db.delete(u)
                await db.commit()
        except Exception:
            pass


if __name__ == "__main__":
    import asyncio
    from backend.database import AsyncSessionLocal
    # Quick standalone exec mock if needed
    async def run_standalone():
        async with AsyncSessionLocal() as session:
            await test_security_phase4(session)
    asyncio.run(run_standalone())
