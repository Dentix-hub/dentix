"""
Slice S36: Controlled Rollout Toggle, Read-Only VNext Mode & Legacy Compatibility Hardening.

Covers:
- G16-M01: Enable internal tenant only (single tenant activation without affecting others).
- G16-M02: Roll out read-only VNext (VNEXT_PRIMARY with native_writes=False; reads work, writes 404).
- G16-M08: Add tenant rollback toggle (atomic instant rollback to LEGACY_ONLY via POST .../rollback).
- G16-M10: Keep legacy compatibility during rollout (legacy treatments sync to native tables; fallback logic preserves chart).
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from backend import models
from backend.auth import create_access_token
from backend.main import app
from backend.models.system import AuditLog
from backend.services.clinical_rollout_service import (
    ClinicalRolloutService,
    FEATURE_FLAG_CLINICAL_SHADOW,
    FEATURE_FLAG_CLINICAL_PRIMARY,
    FEATURE_FLAG_CLINICAL_NATIVE_WRITES,
    FEATURE_FLAG_CLINICAL_FINANCE_READ,
)
from backend.services.clinical_workspace_service import ClinicalWorkspaceService


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
async def s36_seed(async_db_session):
    """Seed two tenants, super admin, doctors, and patients for rollout testing."""
    t1 = models.Tenant(name="Rollout Clinic Alpha", is_active=True)
    t2 = models.Tenant(name="Rollout Clinic Beta", is_active=True)
    async_db_session.add_all([t1, t2])
    await async_db_session.flush()

    super_admin = models.User(
        id=36001,
        username="s36_superadmin",
        email="s36_superadmin@test.com",
        full_name="Super Admin",
        hashed_password="hash",
        role="super_admin",
        tenant_id=None,
        is_active=True,
    )
    doc_alpha = models.User(
        id=36002,
        username="s36_doc_alpha",
        email="s36_doc_alpha@test.com",
        full_name="Dr. Alpha",
        hashed_password="hash",
        role="doctor",
        tenant_id=t1.id,
        is_active=True,
    )
    doc_beta = models.User(
        id=36003,
        username="s36_doc_beta",
        email="s36_doc_beta@test.com",
        full_name="Dr. Beta",
        hashed_password="hash",
        role="doctor",
        tenant_id=t2.id,
        is_active=True,
    )
    async_db_session.add_all([super_admin, doc_alpha, doc_beta])
    await async_db_session.flush()

    pat_alpha = models.Patient(
        name="Patient Alpha",
        age=32,
        phone="01099990001",
        medical_history="None",
        notes="",
        tenant_id=t1.id,
        is_deleted=False,
    )
    pat_beta = models.Patient(
        name="Patient Beta",
        age=45,
        phone="01099990002",
        medical_history="None",
        notes="",
        tenant_id=t2.id,
        is_deleted=False,
    )
    async_db_session.add_all([pat_alpha, pat_beta])
    await async_db_session.commit()

    return {
        "tenant_alpha": t1,
        "tenant_beta": t2,
        "super_admin": super_admin,
        "doc_alpha": doc_alpha,
        "doc_beta": doc_beta,
        "pat_alpha": pat_alpha,
        "pat_beta": pat_beta,
    }


def _auth_headers(user: models.User) -> dict:
    token = create_access_token(
        data={
            "sub": user.username,
            "role": user.role,
            "tenant_id": user.tenant_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# G16-M01: Enable Internal Tenant Only
# ===========================================================================

@pytest.mark.asyncio
async def test_g16_m01_enable_internal_tenant_only(async_db_session, s36_seed):
    """
    Test G16-M01: Activating VNext on Tenant Alpha leaves Tenant Beta strictly in LEGACY_ONLY.
    Verify rollout isolation between internal test clinic and other clinic tenants.
    """
    t_alpha = s36_seed["tenant_alpha"]
    t_beta = s36_seed["tenant_beta"]
    super_admin = s36_seed["super_admin"]
    pat_alpha = s36_seed["pat_alpha"]
    pat_beta = s36_seed["pat_beta"]

    rollout_service = ClinicalRolloutService(async_db_session)

    # Initially both tenants default to LEGACY_ONLY
    status_alpha_init = await rollout_service.get_rollout_status(t_alpha.id)
    status_beta_init = await rollout_service.get_rollout_status(t_beta.id)
    assert status_alpha_init.rollout_mode == "LEGACY_ONLY"
    assert status_beta_init.rollout_mode == "LEGACY_ONLY"

    # Enable internal tenant Alpha only
    res = await rollout_service.set_tenant_rollout_mode(
        tenant_id=t_alpha.id,
        target_mode="VNEXT_PRIMARY_READ_WRITE",
        admin_user=super_admin,
    )
    assert res.success is True
    assert res.current_mode == "VNEXT_PRIMARY"
    assert res.native_writes_enabled is True

    # Re-evaluate statuses: Alpha is VNEXT_PRIMARY, Beta is still LEGACY_ONLY
    status_alpha = await rollout_service.get_rollout_status(t_alpha.id)
    status_beta = await rollout_service.get_rollout_status(t_beta.id)

    assert status_alpha.rollout_mode == "VNEXT_PRIMARY"
    assert status_alpha.native_writes_enabled is True
    assert status_alpha.feature_flags[FEATURE_FLAG_CLINICAL_PRIMARY] is True
    assert status_alpha.feature_flags[FEATURE_FLAG_CLINICAL_NATIVE_WRITES] is True

    assert status_beta.rollout_mode == "LEGACY_ONLY"
    assert status_beta.native_writes_enabled is False
    assert status_beta.feature_flags[FEATURE_FLAG_CLINICAL_PRIMARY] is False
    assert status_beta.feature_flags[FEATURE_FLAG_CLINICAL_NATIVE_WRITES] is False

    # Verify workspace snapshots reflect exact tenant isolation
    ws_alpha = ClinicalWorkspaceService(async_db_session, tenant_id=t_alpha.id)
    ws_beta = ClinicalWorkspaceService(async_db_session, tenant_id=t_beta.id)

    snap_alpha = await ws_alpha.get_workspace_snapshot(pat_alpha.id)
    snap_beta = await ws_beta.get_workspace_snapshot(pat_beta.id)

    assert snap_alpha.read_mode == "VNEXT_PRIMARY"
    assert snap_beta.read_mode == "LEGACY_ONLY"


# ===========================================================================
# G16-M02: Roll Out Read-Only VNext Mode
# ===========================================================================

@pytest.mark.asyncio
async def test_g16_m02_roll_out_read_only_vnext(async_db_session, s36_seed):
    """
    Test G16-M02: VNEXT_PRIMARY with native_writes=False.
    The chart workspace renders from VNext projected data, but standalone native writes
    remain blocked with 404 (fail-closed) to protect against unbilled procedures.
    """
    t_alpha = s36_seed["tenant_alpha"]
    super_admin = s36_seed["super_admin"]
    doc_alpha = s36_seed["doc_alpha"]
    pat_alpha = s36_seed["pat_alpha"]

    rollout_service = ClinicalRolloutService(async_db_session)

    # Set mode to VNEXT_PRIMARY_READ_ONLY
    res = await rollout_service.set_tenant_rollout_mode(
        tenant_id=t_alpha.id,
        target_mode="VNEXT_PRIMARY_READ_ONLY",
        admin_user=super_admin,
    )
    assert res.success is True
    assert res.current_mode == "VNEXT_PRIMARY"
    assert res.native_writes_enabled is False

    # Status check
    status = await rollout_service.get_rollout_status(t_alpha.id)
    assert status.rollout_mode == "VNEXT_PRIMARY"
    assert status.native_writes_enabled is False
    assert status.feature_flags[FEATURE_FLAG_CLINICAL_PRIMARY] is True
    assert status.feature_flags[FEATURE_FLAG_CLINICAL_NATIVE_WRITES] is False

    # Workspace read succeeds in VNEXT_PRIMARY mode
    ws_service = ClinicalWorkspaceService(async_db_session, tenant_id=t_alpha.id)
    snapshot = await ws_service.get_workspace_snapshot(pat_alpha.id)
    assert snapshot.read_mode == "VNEXT_PRIMARY"

    # Standalone native write endpoints fail-closed (404)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Native work item creation is blocked (404)
        wi_payload = {
            "kind": "procedure",
            "code": "REST_COMPOSITE",
            "targets": [{"target_kind": "tooth", "tooth_key": "16"}],
        }
        res_create = await client.post(
            f"/api/v1/patients/{pat_alpha.id}/clinical-work-items",
            json=wi_payload,
            headers=_auth_headers(doc_alpha),
        )
        assert res_create.status_code == 404, "Native writes are blocked in read-only mode!"

        # 2. Care session creation is blocked (404)
        session_payload = {
            "notes": "Restorative Visit",
        }
        res_session = await client.post(
            f"/api/v1/patients/{pat_alpha.id}/care-sessions",
            json=session_payload,
            headers=_auth_headers(doc_alpha),
        )
        assert res_session.status_code == 404, "Care session writes are blocked in read-only mode!"


# ===========================================================================
# G16-M08: Add Tenant Rollback Toggle
# ===========================================================================

@pytest.mark.asyncio
async def test_g16_m08_atomic_tenant_rollback(async_db_session, s36_seed):
    """
    Test G16-M08: Atomically roll back a tenant to LEGACY_ONLY mode in 1 call.
    Instantly disables primary, shadow, native_writes, and finance_read.
    """
    t_alpha = s36_seed["tenant_alpha"]
    super_admin = s36_seed["super_admin"]
    pat_alpha = s36_seed["pat_alpha"]

    rollout_service = ClinicalRolloutService(async_db_session)

    # 1. Activate full VNext with native writes and finance read
    await rollout_service.set_tenant_rollout_mode(
        tenant_id=t_alpha.id,
        target_mode="VNEXT_PRIMARY_READ_WRITE",
        admin_user=super_admin,
    )
    # Also enable finance read
    await rollout_service._apply_flag_overrides(
        t_alpha.id, {FEATURE_FLAG_CLINICAL_FINANCE_READ: True}
    )
    await async_db_session.commit()

    status_before = await rollout_service.get_rollout_status(t_alpha.id)
    assert status_before.rollout_mode == "VNEXT_PRIMARY"
    assert status_before.native_writes_enabled is True
    assert status_before.finance_read_enabled is True

    # 2. Execute atomic rollback
    rollback_res = await rollout_service.rollback_tenant(
        tenant_id=t_alpha.id,
        admin_user=super_admin,
    )
    assert rollback_res.success is True
    assert rollback_res.previous_mode == "VNEXT_PRIMARY"
    assert rollback_res.current_mode == "LEGACY_ONLY"
    assert rollback_res.native_writes_enabled is False

    # 3. Verify all flags are strictly False
    status_after = await rollout_service.get_rollout_status(t_alpha.id)
    assert status_after.rollout_mode == "LEGACY_ONLY"
    assert status_after.native_writes_enabled is False
    assert status_after.finance_read_enabled is False
    for flag_name, flag_val in status_after.feature_flags.items():
        assert flag_val is False, f"Flag {flag_name} must be False after rollback!"

    # 4. Workspace snapshot resolves LEGACY_ONLY immediately
    ws_service = ClinicalWorkspaceService(async_db_session, tenant_id=t_alpha.id)
    snap = await ws_service.get_workspace_snapshot(pat_alpha.id)
    assert snap.read_mode == "LEGACY_ONLY"

    # 5. Audit log entry recorded
    audit_stmt = select(AuditLog).where(
        AuditLog.tenant_id == t_alpha.id,
        AuditLog.action == "clinical_rollout_rollback",
    )
    audit = (await async_db_session.execute(audit_stmt)).scalars().first()
    assert audit is not None
    assert audit.performed_by_id == super_admin.id
    assert "LEGACY_ONLY" in audit.details


@pytest.mark.asyncio
async def test_g16_m08_rollback_from_shadow_mode(async_db_session, s36_seed):
    """
    Test G16-M08: Rollback from SHADOW mode atomically reverts to LEGACY_ONLY.
    """
    t_beta = s36_seed["tenant_beta"]
    super_admin = s36_seed["super_admin"]

    rollout_service = ClinicalRolloutService(async_db_session)

    # Set SHADOW mode
    await rollout_service.set_tenant_rollout_mode(
        tenant_id=t_beta.id,
        target_mode="SHADOW",
        admin_user=super_admin,
    )
    status_shadow = await rollout_service.get_rollout_status(t_beta.id)
    assert status_shadow.rollout_mode == "SHADOW"

    # Rollback
    res = await rollout_service.rollback_tenant(
        tenant_id=t_beta.id,
        admin_user=super_admin,
    )
    assert res.success is True
    assert res.previous_mode == "SHADOW"
    assert res.current_mode == "LEGACY_ONLY"

    status_final = await rollout_service.get_rollout_status(t_beta.id)
    assert status_final.rollout_mode == "LEGACY_ONLY"
    assert status_final.feature_flags[FEATURE_FLAG_CLINICAL_SHADOW] is False


# ===========================================================================
# G16-M10: Keep Legacy Compatibility During Rollout
# ===========================================================================

@pytest.mark.asyncio
async def test_g16_m10_legacy_treatment_sync_invariance_across_modes(async_db_session, s36_seed):
    """
    Test G16-M10: During all rollout modes (LEGACY_ONLY, SHADOW, VNEXT_PRIMARY),
    legacy treatments are created and synced cleanly without errors,
    and legacy fallback seamlessly provides chart data for unmigrated teeth.
    """
    t_alpha = s36_seed["tenant_alpha"]
    pat_alpha = s36_seed["pat_alpha"]
    doc_alpha = s36_seed["doc_alpha"]
    super_admin = s36_seed["super_admin"]

    rollout_service = ClinicalRolloutService(async_db_session)

    # 1. In LEGACY_ONLY mode: add legacy treatment
    await rollout_service.set_tenant_rollout_mode(t_alpha.id, "LEGACY_ONLY", super_admin)
    t1 = models.Treatment(
        patient_id=pat_alpha.id,
        doctor_id=doc_alpha.id,
        tooth_number=11,
        procedure="Composite Filling",
        cost=300.0,
        discount=0.0,
        tenant_id=t_alpha.id,
    )
    async_db_session.add(t1)
    await async_db_session.commit()

    ws = ClinicalWorkspaceService(async_db_session, tenant_id=t_alpha.id)
    snap1 = await ws.get_workspace_snapshot(pat_alpha.id)
    assert snap1.read_mode == "LEGACY_ONLY"
    assert any(item.code == "REST_COMPOSITE" for item in snap1.work_items)

    # 2. In SHADOW mode: add second treatment
    await rollout_service.set_tenant_rollout_mode(t_alpha.id, "SHADOW", super_admin)
    t2 = models.Treatment(
        patient_id=pat_alpha.id,
        doctor_id=doc_alpha.id,
        tooth_number=12,
        procedure="Crown",
        cost=250.0,
        discount=0.0,
        tenant_id=t_alpha.id,
    )
    async_db_session.add(t2)
    await async_db_session.commit()

    snap2 = await ws.get_workspace_snapshot(pat_alpha.id)
    assert snap2.read_mode == "SHADOW"
    assert len(snap2.work_items) >= 2

    # 3. In VNEXT_PRIMARY_READ_ONLY mode: legacy fallback still surfaces legacy treatments
    await rollout_service.set_tenant_rollout_mode(t_alpha.id, "VNEXT_PRIMARY_READ_ONLY", super_admin)
    snap3 = await ws.get_workspace_snapshot(pat_alpha.id)
    assert snap3.read_mode == "VNEXT_PRIMARY"
    # Uncovered treatments fall back gracefully to legacy
    assert len(snap3.work_items) >= 2


# ===========================================================================
# Endpoints & RBAC Verification
# ===========================================================================

@pytest.mark.asyncio
async def test_clinical_rollout_endpoints_and_rbac(async_db_session, s36_seed):
    """
    Test super-admin RBAC on clinical rollout endpoints:
    - Super-admin: 200 OK
    - Doctor: 403 Forbidden
    - Non-existent tenant: 404
    - Invalid mode: 422
    """
    t_alpha = s36_seed["tenant_alpha"]
    super_admin = s36_seed["super_admin"]
    doc_alpha = s36_seed["doc_alpha"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Super-admin get status -> 200
        res_status = await client.get(
            f"/api/v1/admin/clinical-rollout/{t_alpha.id}/status",
            headers=_auth_headers(super_admin),
        )
        assert res_status.status_code == 200
        data = res_status.json()
        assert data["tenant_id"] == t_alpha.id
        assert "rollout_mode" in data
        assert "feature_flags" in data

        # 2. Super-admin set mode -> 200
        res_mode = await client.post(
            f"/api/v1/admin/clinical-rollout/{t_alpha.id}/mode",
            json={"mode": "SHADOW"},
            headers=_auth_headers(super_admin),
        )
        assert res_mode.status_code == 200
        assert res_mode.json()["current_mode"] == "SHADOW"

        # 3. Super-admin rollback -> 200
        res_rb = await client.post(
            f"/api/v1/admin/clinical-rollout/{t_alpha.id}/rollback",
            headers=_auth_headers(super_admin),
        )
        assert res_rb.status_code == 200
        assert res_rb.json()["current_mode"] == "LEGACY_ONLY"

        # 4. Doctor get status -> 403 Forbidden
        res_doc_get = await client.get(
            f"/api/v1/admin/clinical-rollout/{t_alpha.id}/status",
            headers=_auth_headers(doc_alpha),
        )
        assert res_doc_get.status_code == 403

        # 5. Doctor rollback -> 403 Forbidden
        res_doc_rb = await client.post(
            f"/api/v1/admin/clinical-rollout/{t_alpha.id}/rollback",
            headers=_auth_headers(doc_alpha),
        )
        assert res_doc_rb.status_code == 403

        # 6. Non-existent tenant -> 404
        res_missing = await client.get(
            "/api/v1/admin/clinical-rollout/999999/status",
            headers=_auth_headers(super_admin),
        )
        assert res_missing.status_code == 404

        # 7. Invalid mode -> 422 Unprocessable Entity
        res_bad_mode = await client.post(
            f"/api/v1/admin/clinical-rollout/{t_alpha.id}/mode",
            json={"mode": "INVALID_MODE"},
            headers=_auth_headers(super_admin),
        )
        assert res_bad_mode.status_code == 422
