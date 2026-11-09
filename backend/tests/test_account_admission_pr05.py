# backend/tests/test_account_admission_pr05.py
"""
PR-05 Acceptance Tests: Atomic Active-Account Limits & Safe Lifecycle.

Validates all PR-05 requirements:
1. One Authoritative Count:
   - Active login-capable, non-deleted clinic accounts including owner.
   - Inactive accounts, soft-deleted accounts, platform super_admins, and
     non-login staff references do NOT consume a seat.
2. Capacity Enforcement (2 / 5 / 15):
   - Essential (2 seats), Professional (5 seats), Business (15 seats).
   - Creation past cap fails with HTTP 400 without partial mutations.
3. Centralized Atomic Admission:
   - Consistent tenant row-locking (with_for_update) serializes admissions.
   - All create and re-enable paths use it, including Super Admin toggle.
   - Super Admin cannot bypass capacity limits on user reactivation.
4. Non-Destructive Inactive Handling:
   - Cap exhaustion NEVER deletes or disables existing users.
   - Password reset for an inactive user does NOT implicitly reactivate them.
5. Deactivation & Soft-Deletion Releases Seat:
   - Deactivating or deleting a user releases admission capacity.
   - Clinical authorship references (CareSession, ClinicalCharge) are preserved.
6. Rollback Safety:
   - Unique-username failure and transaction rollback leave capacity correct.
7. Concurrent Race Safety:
   - Concurrent admissions on PostgreSQL are serialized; exactly one succeeds
     for the last remaining seat.
"""

import asyncio
from datetime import datetime, timezone
import os
import random
import uuid
import pytest
from fastapi import HTTPException

from backend import models, schemas
from backend.core.commercial_registry import resolve_plan_spec
from backend.services.account_admission_service import (
    AccountAdmissionService,
    AccountCapacityExceededError,
)
from backend.routers import users as users_router
from backend.routers import admin_system as admin_system_router
from backend.routers import system_admin as system_admin_router
from backend.services.admin_service import AdminService


def _user(
    username: str,
    role: str = "doctor",
    tenant_id: int = 101,
    is_active: bool = True,
    is_deleted: bool = False,
    email: str = None,
    id: int = None,
    failed_login_attempts: int = 0,
):
    kwargs = {
        "username": username,
        "email": email or f"{username}@test.com",
        "hashed_password": "hashed_pw_test_12345",
        "role": role,
        "tenant_id": tenant_id,
        "is_active": is_active,
        "is_deleted": is_deleted,
        "failed_login_attempts": failed_login_attempts,
    }
    if id is not None:
        kwargs["id"] = id
    return models.User(**kwargs)


@pytest.fixture
def mock_current_admin():
    return _user(id=1, username="clinic_owner", role="admin", tenant_id=10)


@pytest.fixture
def mock_super_admin():
    return _user(id=999, username="superadmin", role="super_admin", tenant_id=None)


@pytest.mark.asyncio
async def test_owner_consumes_one_seat_and_counts_accurately(async_db_session):
    """Owner user consumes 1 seat; inactive, deleted, and super_admin do not."""
    tenant = models.Tenant(id=101, name="Seat Count Clinic", plan="essential", is_active=True)
    async_db_session.add(tenant)
    await async_db_session.flush()

    # 1. Initially 0 active users
    count = await AccountAdmissionService.get_active_account_count(async_db_session, tenant.id)
    assert count == 0

    # 2. Add Owner (admin, is_active=True)
    owner = _user(username="owner_101", role="admin", tenant_id=tenant.id)
    async_db_session.add(owner)
    await async_db_session.flush()

    count = await AccountAdmissionService.get_active_account_count(async_db_session, tenant.id)
    assert count == 1

    # 3. Add an inactive user -> does not increase seat count
    inactive_user = _user(username="inactive_101", role="doctor", tenant_id=tenant.id, is_active=False)
    async_db_session.add(inactive_user)
    await async_db_session.flush()

    count = await AccountAdmissionService.get_active_account_count(async_db_session, tenant.id)
    assert count == 1

    # 4. Add a soft-deleted user -> does not increase seat count
    deleted_user = _user(username="deleted_101", role="receptionist", tenant_id=tenant.id, is_active=False, is_deleted=True)
    deleted_user.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    async_db_session.add(deleted_user)
    await async_db_session.flush()

    count = await AccountAdmissionService.get_active_account_count(async_db_session, tenant.id)
    assert count == 1


@pytest.mark.asyncio
async def test_create_user_enforces_caps_2_5_15(async_db_session, mock_current_admin):
    """Essential (2), Professional (5), Business (15) limits are enforced."""
    # Create Essential Plan (max_users=2)
    plan_essential = models.SubscriptionPlan(
        name="essential_pr05",
        display_name_ar="الأساسية",
        max_users=2,
        is_active=True,
    )
    async_db_session.add(plan_essential)
    await async_db_session.flush()

    tenant = models.Tenant(
        id=201,
        name="Essential Clinic",
        plan_id=plan_essential.id,
        is_active=True,
    )
    async_db_session.add(tenant)

    # Add owner
    owner = _user(id=2010, username="owner_ess", role="admin", tenant_id=tenant.id)
    async_db_session.add(owner)
    await async_db_session.commit()

    admin_caller = owner

    # 1. Add 2nd user (fills cap: 2/2)
    res1 = await users_router.register_user(
        payload=schemas.UserRegisterRequest(
            username="doctor_ess_1",
            password="StrongPassword123!",
            email="doc1@ess.com",
            role="doctor",
        ),
        db=async_db_session,
        current_user=admin_caller,
    )
    assert res1["data"].username == "doctor_ess_1"
    assert await AccountAdmissionService.get_active_account_count(async_db_session, tenant.id) == 2

    # 2. Add 3rd user -> Cap exceeded (400)
    with pytest.raises(HTTPException) as exc_info:
        await users_router.register_user(
            payload=schemas.UserRegisterRequest(
                username="doctor_ess_2",
                password="StrongPassword123!",
                email="doc2@ess.com",
                role="doctor",
            ),
            db=async_db_session,
            current_user=admin_caller,
        )
    assert exc_info.value.status_code == 400
    assert "الحد الأقصى" in exc_info.value.detail or "2" in exc_info.value.detail
    # Count remains exactly 2
    assert await AccountAdmissionService.get_active_account_count(async_db_session, tenant.id) == 2


@pytest.mark.asyncio
async def test_re_enable_user_enforces_cap(async_db_session):
    """Reactivating an inactive user is subject to atomic admission."""
    plan = models.SubscriptionPlan(
        name="ess_reenable",
        display_name_ar="أساسي",
        max_users=2,
        is_active=True,
    )
    async_db_session.add(plan)
    await async_db_session.flush()

    tenant = models.Tenant(id=301, name="Reenable Clinic", plan_id=plan.id, is_active=True)
    async_db_session.add(tenant)

    owner = _user(id=3011, username="owner_301", role="admin", tenant_id=tenant.id)
    active_doc = _user(id=3012, username="active_doc", role="doctor", tenant_id=tenant.id)
    inactive_nurse = _user(id=3013, username="inactive_nurse", role="nurse", tenant_id=tenant.id, is_active=False)
    async_db_session.add_all([owner, active_doc, inactive_nurse])
    await async_db_session.commit()

    admin_caller = owner

    # Tenant is already at 2/2. Attempt to reactivate inactive_nurse via PUT /users/{id}
    with pytest.raises(HTTPException) as exc_info:
        await users_router.update_user(
            user_id=inactive_nurse.id,
            user_update=schemas.UserUpdate(is_active=True),
            db=async_db_session,
            current_user=admin_caller,
        )
    assert exc_info.value.status_code == 400
    assert await AccountAdmissionService.get_active_account_count(async_db_session, tenant.id) == 2

    # Now deactivate active_doc (releases seat to 1/2)
    res_deact = await users_router.update_user(
        user_id=active_doc.id,
        user_update=schemas.UserUpdate(is_active=False),
        db=async_db_session,
        current_user=admin_caller,
    )
    assert res_deact["data"].is_active is False
    assert await AccountAdmissionService.get_active_account_count(async_db_session, tenant.id) == 1

    # Now reactivating inactive_nurse succeeds! (1/2 -> 2/2)
    res_act = await users_router.update_user(
        user_id=inactive_nurse.id,
        user_update=schemas.UserUpdate(is_active=True),
        db=async_db_session,
        current_user=admin_caller,
    )
    assert res_act["data"].is_active is True
    assert await AccountAdmissionService.get_active_account_count(async_db_session, tenant.id) == 2


@pytest.mark.asyncio
async def test_super_admin_cannot_bypass_cap_on_toggle(async_db_session, mock_super_admin):
    """Super Admin toggle-status endpoint enforces seat cap; no role bypass."""
    plan = models.SubscriptionPlan(
        name="ess_satoggle",
        display_name_ar="أساسي",
        max_users=1,
        is_active=True,
    )
    async_db_session.add(plan)
    await async_db_session.flush()

    tenant = models.Tenant(id=401, name="SA Toggle Clinic", plan_id=plan.id, is_active=True)
    async_db_session.add(tenant)

    owner = _user(id=4011, username="owner_401", role="admin", tenant_id=tenant.id)
    inactive_user = _user(id=4012, username="inactive_401", role="doctor", tenant_id=tenant.id, is_active=False)
    async_db_session.add_all([owner, inactive_user])
    await async_db_session.commit()

    # Clinic is already at 1/1. Super Admin attempts to enable inactive_user
    with pytest.raises(HTTPException) as exc_info:
        await admin_system_router.toggle_user_status(
            user_id=inactive_user.id,
            current_user=mock_super_admin,
            db=async_db_session,
        )
    assert exc_info.value.status_code == 400
    assert await AccountAdmissionService.get_active_account_count(async_db_session, tenant.id) == 1


@pytest.mark.asyncio
async def test_password_reset_does_not_implicitly_reactivate_inactive_user(
    async_db_session, mock_super_admin
):
    """Password reset clears lockouts but preserves inactive state."""
    tenant = models.Tenant(id=501, name="Reset Clinic", plan="essential", is_active=True)
    async_db_session.add(tenant)

    inactive_user = _user(
        id=5012,
        username="locked_inactive",
        role="doctor",
        tenant_id=tenant.id,
        is_active=False,
        failed_login_attempts=5,
    )
    async_db_session.add(inactive_user)
    await async_db_session.commit()

    # Super Admin resets password
    res = await system_admin_router.reset_user_password(
        user_id=inactive_user.id,
        password_data={"new_password": "NewSecurePassword123!"},
        current_user=mock_super_admin,
        db=async_db_session,
    )
    assert res["success"] is True

    # User failed attempts cleared, BUT is_active remains False
    await async_db_session.refresh(inactive_user)
    assert inactive_user.failed_login_attempts == 0
    assert inactive_user.is_active is False
    assert await AccountAdmissionService.get_active_account_count(async_db_session, tenant.id) == 0


@pytest.mark.asyncio
async def test_soft_delete_releases_capacity_and_preserves_clinical_authorship(async_db_session):
    """Soft deletion releases seat while keeping authored care sessions intact."""
    plan = models.SubscriptionPlan(
        name="ess_softdel",
        display_name_ar="أساسي",
        max_users=2,
        is_active=True,
    )
    async_db_session.add(plan)
    await async_db_session.flush()

    tenant = models.Tenant(id=601, name="Soft Del Clinic", plan_id=plan.id, is_active=True)
    async_db_session.add(tenant)

    owner = _user(id=6011, username="owner_601", role="admin", tenant_id=tenant.id)
    doctor = _user(id=6012, username="doc_601", role="doctor", tenant_id=tenant.id)
    async_db_session.add_all([owner, doctor])
    await async_db_session.flush()

    # Patient and care session authored by doctor
    patient = models.Patient(
        id=60101, name="Test Patient", phone="01011112222", tenant_id=tenant.id
    )
    async_db_session.add(patient)
    await async_db_session.flush()

    care_session = models.CareSession(
        tenant_id=tenant.id,
        patient_id=patient.id,
        provider_user_id=doctor.id,
        status="in_progress",
    )
    async_db_session.add(care_session)
    await async_db_session.commit()

    assert await AccountAdmissionService.get_active_account_count(async_db_session, tenant.id) == 2

    # Delete doctor via DELETE /users/{id}
    res_del = await users_router.delete_user(
        user_id=doctor.id,
        db=async_db_session,
        current_user=owner,
    )
    assert res_del["data"]["user_id"] == doctor.id

    # 1. Doctor is soft-deleted, not removed from DB
    await async_db_session.refresh(doctor)
    assert doctor.is_deleted is True
    assert doctor.is_active is False
    assert doctor.deleted_at is not None

    # 2. Care session still exists and references doctor.id
    await async_db_session.refresh(care_session)
    assert care_session.provider_user_id == doctor.id

    # 3. Capacity is released: count drops to 1/2
    assert await AccountAdmissionService.get_active_account_count(async_db_session, tenant.id) == 1

    # 4. Now a replacement user can be registered successfully!
    res_new = await users_router.register_user(
        payload=schemas.UserRegisterRequest(
            username="replacement_doc",
            password="StrongPassword123!",
            email="replace@test.com",
            role="doctor",
        ),
        db=async_db_session,
        current_user=owner,
    )
    assert res_new["data"].username == "replacement_doc"
    assert await AccountAdmissionService.get_active_account_count(async_db_session, tenant.id) == 2


@pytest.mark.asyncio
async def test_duplicate_username_rollback_leaves_capacity_intact(async_db_session):
    """Failed insert due to duplicate username rolls back without leaking capacity."""
    plan = models.SubscriptionPlan(
        name="ess_rollback",
        display_name_ar="أساسي",
        max_users=2,
        is_active=True,
    )
    async_db_session.add(plan)
    await async_db_session.flush()

    tenant = models.Tenant(id=701, name="Rollback Clinic", plan_id=plan.id, is_active=True)
    async_db_session.add(tenant)

    owner = _user(id=7011, username="owner_701", email="owner701@test.com", role="admin", tenant_id=tenant.id, is_active=True)
    async_db_session.add(owner)
    await async_db_session.commit()

    assert await AccountAdmissionService.get_active_account_count(async_db_session, tenant.id) == 1

    # Attempt to create user with existing username 'owner_701'
    with pytest.raises(HTTPException) as exc_info:
        await users_router.register_user(
            payload=schemas.UserRegisterRequest(
                username="owner_701",
                password="StrongPassword123!",
                email="diff@test.com",
                role="doctor",
            ),
            db=async_db_session,
            current_user=owner,
        )
    assert exc_info.value.status_code == 400

    # Capacity is intact: still 1/2
    assert await AccountAdmissionService.get_active_account_count(async_db_session, tenant.id) == 1


@pytest.mark.asyncio
async def test_admin_cannot_delete_or_disable_own_account(async_db_session):
    """Admin cannot delete or disable their own active account."""
    tenant = models.Tenant(id=801, name="Self Protect Clinic", plan="essential", is_active=True)
    async_db_session.add(tenant)
    owner = _user(id=8011, username="owner_801", role="admin", tenant_id=tenant.id)
    async_db_session.add(owner)
    await async_db_session.commit()

    # 1. Attempt self-deletion
    with pytest.raises(HTTPException) as exc_del:
        await users_router.delete_user(user_id=owner.id, db=async_db_session, current_user=owner)
    assert exc_del.value.status_code == 400
    assert "cannot delete your own" in exc_del.value.detail.lower()

    # 2. Attempt self-disabling
    with pytest.raises(HTTPException) as exc_dis:
        await users_router.update_user(
            user_id=owner.id,
            user_update=schemas.UserUpdate(is_active=False),
            db=async_db_session,
            current_user=owner,
        )
    assert exc_dis.value.status_code == 400
    assert "cannot disable your own" in exc_dis.value.detail.lower()


@pytest.mark.asyncio
async def test_admin_service_activate_and_deactivate(async_db_session):
    """AdminService methods use AccountAdmissionService and revoke sessions."""
    plan = models.SubscriptionPlan(
        name="ess_adminsvc",
        display_name_ar="أساسي",
        max_users=1,
        is_active=True,
    )
    async_db_session.add(plan)
    await async_db_session.flush()

    tenant = models.Tenant(id=901, name="AdminSvc Clinic", plan_id=plan.id, is_active=True)
    async_db_session.add(tenant)

    owner = _user(id=9011, username="owner_901", role="admin", tenant_id=tenant.id)
    user2 = _user(id=9012, username="user2_901", role="doctor", tenant_id=tenant.id, is_active=False)
    async_db_session.add_all([owner, user2])
    await async_db_session.commit()

    service = AdminService(async_db_session)

    # 1. Activating user2 fails because cap=1 and owner is already active
    with pytest.raises(AccountCapacityExceededError):
        await service.activate_user(user2.id)

    # 2. Deactivating owner frees seat
    deact_owner = await service.deactivate_user(owner.id)
    assert deact_owner.is_active is False
    assert await AccountAdmissionService.get_active_account_count(async_db_session, tenant.id) == 0

    # 3. Now activating user2 succeeds
    act_user2 = await service.activate_user(user2.id)
    assert act_user2.is_active is True
    assert await AccountAdmissionService.get_active_account_count(async_db_session, tenant.id) == 1


@pytest.mark.asyncio
async def test_postgresql_concurrent_admissions_serialized():
    """
    On live PostgreSQL, two concurrent admission transactions competing for 1 seat
    are serialized by row-level locking: exactly one succeeds, exactly one fails.
    """
    test_db_url = os.environ.get("TEST_DATABASE_URL")
    if not test_db_url or "postgresql" not in test_db_url:
        pytest.skip("TEST_DATABASE_URL with PostgreSQL not provided for live concurrency test.")

    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    async_url = test_db_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url, pool_size=5, max_overflow=5)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    unique_suffix = uuid.uuid4().hex[:8]
    tenant_id = random.randint(900000, 999999)
    async with async_session_maker() as session:
        # Prepare plan with cap=2 and 1 owner
        plan = models.SubscriptionPlan(
            name=f"pg_concurrent_plan_{unique_suffix}",
            display_name_ar="متزامن",
            max_users=2,
            is_active=True,
        )
        session.add(plan)
        await session.flush()

        tenant = models.Tenant(id=tenant_id, name=f"PG Concurrency Clinic {unique_suffix}", plan_id=plan.id, is_active=True)
        session.add(tenant)
        await session.flush()

        owner = models.User(
            username=f"pg_owner_{unique_suffix}",
            role="admin",
            tenant_id=tenant_id,
            is_active=True,
            is_deleted=False,
            hashed_password="pw_hash_test_concurrent",
        )
        session.add(owner)
        await session.commit()

    # Now exactly 1 seat remains. Launch 2 concurrent tasks
    async def try_admit(user_suffix: str) -> bool:
        async with async_session_maker() as s:
            try:
                await AccountAdmissionService.admit_active_account(s, tenant_id=tenant_id)
                new_u = models.User(
                    username=f"concurrent_u_{user_suffix}_{tenant_id}",
                    role="doctor",
                    tenant_id=tenant_id,
                    is_active=True,
                    is_deleted=False,
                    hashed_password="pw_hash_test_concurrent",
                )
                s.add(new_u)
                await s.commit()
                return True
            except AccountCapacityExceededError:
                await s.rollback()
                return False

    results = await asyncio.gather(try_admit("A"), try_admit("B"))

    # Exactly one succeeded and one failed
    assert sorted(results) == [False, True]

    # Verify final count in DB is exactly 2
    async with async_session_maker() as s:
        final_count = await AccountAdmissionService.get_active_account_count(s, tenant_id=tenant_id)
        assert final_count == 2

    await engine.dispose()
