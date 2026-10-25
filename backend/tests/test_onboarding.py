"""Tests for onboarding checklist and first-visit tooltips."""

import pytest
from datetime import datetime, timezone
from sqlalchemy import select

from backend import models
from backend.auth import create_access_token, get_password_hash
from backend.services.feature_service import FeatureFlagService
from backend.services.onboarding_service import OnboardingService


def _headers(user):
    token = create_access_token(
        data={"sub": user.username, "role": user.role, "tenant_id": user.tenant_id}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def onboarding_flag(db_session):
    flag = db_session.execute(
        select(models.FeatureFlag).where(models.FeatureFlag.key == "onboarding_checklist")
    ).scalar_one_or_none()
    if not flag:
        flag = models.FeatureFlag(
            key="onboarding_checklist",
            description="Onboarding checklist",
            is_global_enabled=True,
            rollout_percentage=100,
        )
        db_session.add(flag)
    else:
        flag.is_global_enabled = True
        flag.rollout_percentage = 100
    db_session.commit()
    return flag


def test_effective_state_matrix_2x3(client, db_session, test_tenant, super_admin_headers, auth_headers):
    """Test 2x3 matrix: global (ON, OFF) x override (inherit, force ON, force OFF)."""
    # Ensure flag exists
    flag = db_session.execute(
        select(models.FeatureFlag).where(models.FeatureFlag.key == "onboarding_checklist")
    ).scalar_one_or_none()
    if not flag:
        flag = models.FeatureFlag(
            key="onboarding_checklist",
            description="Onboarding checklist",
            is_global_enabled=True,
            rollout_percentage=100,
        )
        db_session.add(flag)
        db_session.commit()

    cases = [
        # (global_on, override_val, expected_effective)
        (True, None, True),      # Global ON, inherit -> ON
        (True, True, True),      # Global ON, force ON -> ON
        (True, False, False),    # Global ON, force OFF -> OFF
        (False, None, False),    # Global OFF, inherit -> OFF
        (False, True, True),     # Global OFF, force ON -> ON
        (False, False, False),   # Global OFF, force OFF -> OFF
    ]

    for global_on, override_val, expected_effective in cases:
        # Set global
        flag.is_global_enabled = global_on
        db_session.commit()

        # Set or delete override
        if override_val is None:
            del_res = client.delete(
                "/api/v1/admin/features/override",
                params={"tenant_id": test_tenant.id, "feature_key": "onboarding_checklist"},
                headers=super_admin_headers,
            )
            assert del_res.status_code in (200, 404)
        else:
            set_res = client.post(
                "/api/v1/admin/features/override",
                json={
                    "tenant_id": test_tenant.id,
                    "feature_key": "onboarding_checklist",
                    "is_enabled": override_val,
                },
                headers=super_admin_headers,
            )
            assert set_res.status_code == 200

        # Check tenant status endpoint
        status_res = client.get(
            f"/api/v1/admin/features/tenant/{test_tenant.id}/onboarding_checklist",
            headers=super_admin_headers,
        )
        assert status_res.status_code == 200
        data = status_res.json()
        assert data["effective"] == expected_effective, (
            f"Failed for global={global_on}, override={override_val}: expected {expected_effective}"
        )

        # Check tenant caller status
        caller_res = client.get("/api/v1/onboarding/status", headers=auth_headers)
        assert caller_res.status_code == 200
        caller_data = caller_res.json()
        assert caller_data["enabled"] == expected_effective


def test_delete_override_security_and_non_super_admin_403(client, test_tenant, auth_headers, super_admin_headers, onboarding_flag):
    """Non-super-admin gets 403 on override delete."""
    # Regular user attempting DELETE
    res = client.delete(
        "/api/v1/admin/features/override",
        params={"tenant_id": test_tenant.id, "feature_key": "onboarding_checklist"},
        headers=auth_headers,
    )
    assert res.status_code == 403

    # Super admin succeeds
    res_ok = client.delete(
        "/api/v1/admin/features/override",
        params={"tenant_id": test_tenant.id, "feature_key": "onboarding_checklist"},
        headers=super_admin_headers,
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "success"


def test_role_mapping(client, db_session, test_tenant, onboarding_flag):
    """Test checklist role mapping: admin (manager+doctor), manager, doctor, reception, accountant, nurse (none)."""
    roles = [
        ("admin", ["manager", "doctor"]),
        ("manager", ["manager"]),
        ("doctor", ["doctor"]),
        ("receptionist", ["reception"]),
        ("accountant", ["accountant"]),
    ]

    for role_name, expected_section_ids in roles:
        user = models.User(
            username=f"user_{role_name}",
            email=f"{role_name}@example.com",
            hashed_password=get_password_hash("pass123"),
            role=role_name,
            tenant_id=test_tenant.id,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        res = client.get("/api/v1/onboarding/status", headers=_headers(user))
        assert res.status_code == 200
        data = res.json()
        assert data["enabled"] is True
        section_ids = [s["id"] for s in data["sections"]]
        assert section_ids == expected_section_ids, f"Role {role_name} got {section_ids}"

    # Nurse gets disabled / no steps
    nurse = models.User(
        username="user_nurse",
        email="nurse@example.com",
        hashed_password=get_password_hash("pass123"),
        role="nurse",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add(nurse)
    db_session.commit()

    nurse_res = client.get("/api/v1/onboarding/status", headers=_headers(nurse))
    assert nurse_res.status_code == 200
    assert nurse_res.json()["enabled"] is False
    assert nurse_res.json()["steps"] == []


def test_hidden_steps_when_flag_unavailable(client, db_session, test_tenant, onboarding_flag):
    """Test D4 hidden when clinical_treatment_plans is off; A1 hidden when clinical_vnext_native_writes is off."""
    # Ensure clinical_treatment_plans is disabled
    tf_d4 = models.TenantFeature(
        tenant_id=test_tenant.id,
        feature_key="clinical_treatment_plans",
        is_enabled=False,
    )
    # Ensure clinical_vnext_native_writes is disabled
    tf_a1 = models.TenantFeature(
        tenant_id=test_tenant.id,
        feature_key="clinical_vnext_native_writes",
        is_enabled=False,
    )
    db_session.merge(tf_d4)
    db_session.merge(tf_a1)
    db_session.commit()

    # Doctor check: D4 must not appear in steps
    doc = models.User(
        username="test_doc_hidden",
        email="doc_hidden@example.com",
        hashed_password=get_password_hash("pass123"),
        role="doctor",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add(doc)
    db_session.commit()

    doc_res = client.get("/api/v1/onboarding/status", headers=_headers(doc))
    doc_data = doc_res.json()
    step_keys = [s["key"] for s in doc_data["steps"]]
    assert "D4" not in step_keys
    # Total progress excludes D4
    assert doc_data["progress"]["total"] == len(doc_data["steps"])

    # Accountant check: A1 must not appear in steps
    acc = models.User(
        username="test_acc_hidden",
        email="acc_hidden@example.com",
        hashed_password=get_password_hash("pass123"),
        role="accountant",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add(acc)
    db_session.commit()

    acc_res = client.get("/api/v1/onboarding/status", headers=_headers(acc))
    acc_data = acc_res.json()
    acc_step_keys = [s["key"] for s in acc_data["steps"]]
    assert "A1" not in acc_step_keys
    assert acc_data["progress"]["total"] == len(acc_data["steps"])


def test_events_endpoint_whitelist_and_dismiss_flow(client, db_session, test_tenant, test_user, auth_headers, onboarding_flag):
    """Test events endpoint rejects non-whitelisted keys and dismiss/restore flow."""
    # Invalid event key -> 400
    res_bad = client.post(
        "/api/v1/onboarding/events",
        json={"event_key": "arbitrary_untrusted_event"},
        headers=auth_headers,
    )
    assert res_bad.status_code == 400

    # Whitelisted event key -> 200
    res_good = client.post(
        "/api/v1/onboarding/events",
        json={"event_key": "patient_file_opened"},
        headers=auth_headers,
    )
    assert res_good.status_code == 200
    assert res_good.json()["event_key"] == "patient_file_opened"

    # Tip seen -> 200
    res_tip = client.post(
        "/api/v1/onboarding/tips/chart_click_tip",
        headers=auth_headers,
    )
    assert res_tip.status_code == 200
    assert "chart_click_tip" in res_tip.json()["seen_tips"]

    # Dismiss -> 200
    res_dismiss = client.post(
        "/api/v1/onboarding/dismiss",
        json={"dismissed": True},
        headers=auth_headers,
    )
    assert res_dismiss.status_code == 200
    assert res_dismiss.json()["dismissed"] is True

    # Status reflects dismissed
    res_status = client.get("/api/v1/onboarding/status", headers=auth_headers)
    assert res_status.json()["dismissed"] is True
    assert "chart_click_tip" in res_status.json()["seen_tips"]

    # Restore -> 200
    res_restore = client.post("/api/v1/onboarding/restore", headers=auth_headers)
    assert res_restore.status_code == 200
    assert res_restore.json()["dismissed"] is False

    # Status reflects restored
    res_status2 = client.get("/api/v1/onboarding/status", headers=auth_headers)
    assert res_status2.json()["dismissed"] is False


def test_signal_computation_and_tenant_isolation(client, db_session, test_tenant, onboarding_flag):
    """Verify signals: procedures (M2), tooth_status/clinical_findings (D2), soft-delete ignored, tenant isolation."""
    # Create second tenant
    tenant_b = models.Tenant(name="Tenant B Clinic", is_active=True)
    db_session.add(tenant_b)
    db_session.commit()

    admin_a = models.User(
        username="admin_tenant_a",
        email="admin_a@example.com",
        hashed_password=get_password_hash("pass123"),
        role="admin",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    admin_b = models.User(
        username="admin_tenant_b",
        email="admin_b@example.com",
        hashed_password=get_password_hash("pass123"),
        role="admin",
        tenant_id=tenant_b.id,
        is_active=True,
    )
    db_session.add_all([admin_a, admin_b])
    db_session.commit()

    # At start, newly created tenant has 0 procedures, so M2 is False
    res_a_start = client.get("/api/v1/onboarding/status", headers=_headers(admin_a))
    steps_a_start = {s["key"]: s["done"] for s in res_a_start.json()["steps"]}
    assert steps_a_start["M2"] is False
    assert steps_a_start["D2"] is False

    # Add procedure to Tenant B ONLY
    proc_b = models.Procedure(name="Scaling", price=100.0, tenant_id=tenant_b.id)
    db_session.add(proc_b)
    db_session.commit()

    # Tenant A still False (tenant isolation)
    res_a = client.get("/api/v1/onboarding/status", headers=_headers(admin_a))
    steps_a = {s["key"]: s["done"] for s in res_a.json()["steps"]}
    assert steps_a["M2"] is False

    # Tenant B has M2 = True
    res_b = client.get("/api/v1/onboarding/status", headers=_headers(admin_b))
    steps_b = {s["key"]: s["done"] for s in res_b.json()["steps"]}
    assert steps_b["M2"] is True

    # Test D2 dual write paths:
    # 1. ToothStatus with condition != 'Healthy'
    patient_a = models.Patient(
        name="Patient A", age=30, phone="01012345678", medical_history="", notes="", tenant_id=test_tenant.id, is_deleted=False
    )
    db_session.add(patient_a)
    db_session.commit()

    ts = models.ToothStatus(
        tenant_id=test_tenant.id,
        patient_id=patient_a.id,
        tooth_number=11,
        condition="Caries",
    )
    db_session.add(ts)
    db_session.commit()

    res_a_d2 = client.get("/api/v1/onboarding/status", headers=_headers(admin_a))
    steps_a_d2 = {s["key"]: s["done"] for s in res_a_d2.json()["steps"]}
    assert steps_a_d2["D2"] is True

    # Soft-deleted patient ignored in R1
    patient_deleted = models.Patient(
        name="Deleted Patient", age=25, phone="01087654321", medical_history="", notes="", tenant_id=tenant_b.id, is_deleted=True
    )
    db_session.add(patient_deleted)
    db_session.commit()

    rec_b = models.User(
        username="rec_b",
        email="rec_b@example.com",
        hashed_password=get_password_hash("pass123"),
        role="receptionist",
        tenant_id=tenant_b.id,
        is_active=True,
    )
    db_session.add(rec_b)
    db_session.commit()

    res_rec_b = client.get("/api/v1/onboarding/status", headers=_headers(rec_b))
    steps_rec_b = {s["key"]: s["done"] for s in res_rec_b.json()["steps"]}
    # R1 must still be False because patient is soft-deleted
    assert steps_rec_b["R1"] is False

    # Test R4: active patient with chronic condition in medical_history
    patient_chronic = models.Patient(
        name="Chronic Patient",
        age=45,
        phone="01099998888",
        medical_history="يعاني من ارتفاع ضغط الدم والسكري",
        notes="",
        tenant_id=tenant_b.id,
        is_deleted=False,
    )
    db_session.add(patient_chronic)
    db_session.commit()

    res_rec_b2 = client.get("/api/v1/onboarding/status", headers=_headers(rec_b))
    steps_rec_b2 = {s["key"]: s["done"] for s in res_rec_b2.json()["steps"]}
    assert steps_rec_b2["R4"] is True
    assert steps_rec_b2["R1"] is True


def test_alembic_onboarding_migration_lifecycle_sqlite(monkeypatch):
    """Rehearse Alembic migrations 7a8b9c0d1e2f and 8b9c0d1e2f3a upgrade and downgrade on SQLite."""
    import os
    import tempfile
    from alembic import command
    from alembic.config import Config
    import sqlalchemy as sa

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        sqlite_url = f"sqlite:///{db_path}"
        monkeypatch.setenv("DATABASE_URL", sqlite_url)
        engine = sa.create_engine(sqlite_url)
        alembic_cfg_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
        )
        config = Config(alembic_cfg_path)
        config.set_main_option("sqlalchemy.url", sqlite_url)

        # 1. Base tables needed
        with engine.connect() as conn:
            conn.execute(sa.text("CREATE TABLE tenants (id INTEGER PRIMARY KEY, name VARCHAR)"))
            conn.execute(sa.text("CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR, tenant_id INTEGER)"))
            conn.execute(
                sa.text(
                    """CREATE TABLE feature_flags (
                        id INTEGER PRIMARY KEY,
                        key VARCHAR UNIQUE,
                        description VARCHAR,
                        is_global_enabled BOOLEAN,
                        rollout_percentage INTEGER
                    )"""
                )
            )
            conn.commit()

        # 2. Stamp at 6f7a8b9c0d1e (parent revision)
        command.stamp(config, "6f7a8b9c0d1e")

        # 3. Upgrade to Migration A (7a8b9c0d1e2f)
        command.upgrade(config, "7a8b9c0d1e2f")
        insp = sa.inspect(engine)
        assert "user_onboarding_state" in insp.get_table_names()
        cols = {c["name"] for c in insp.get_columns("user_onboarding_state")}
        assert {"id", "tenant_id", "user_id", "dismissed", "seen_tips", "events", "updated_at"}.issubset(cols)

        # 3. Upgrade to Migration B (8b9c0d1e2f3a)
        command.upgrade(config, "8b9c0d1e2f3a")
        with engine.connect() as conn:
            row = conn.execute(
                sa.text("SELECT key, is_global_enabled, rollout_percentage FROM feature_flags WHERE key = 'onboarding_checklist'")
            ).fetchone()
            assert row is not None
            assert row[0] == "onboarding_checklist"
            assert row[1] in (1, True)
            assert row[2] == 100

        # 4. Downgrade to Migration A
        command.downgrade(config, "7a8b9c0d1e2f")
        with engine.connect() as conn:
            row_down = conn.execute(
                sa.text("SELECT key FROM feature_flags WHERE key = 'onboarding_checklist'")
            ).fetchone()
            assert row_down is None

        # 5. Downgrade to prior head (6f7a8b9c0d1e)
        command.downgrade(config, "6f7a8b9c0d1e")
        insp_down = sa.inspect(engine)
        assert "user_onboarding_state" not in insp_down.get_table_names()

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

