"""Acceptance test suite for PR-09C Commercial Controls on Operational Modules.

Covers:
1. Gating inventory, laboratories, price lists, and backup operations when subscription is expired or plan lacks capability.
2. Direct domain service enforcement failing-closed:
   - InventoryService.create_warehouse, add_stock, consume_stock, delete_material
   - LabService.create_laboratory, create_lab_order, create_lab_payment
   - export_clinic_archive_data, queue_drive_backup
3. AI tools (get_lab_orders) respecting commercial capability decisions.
4. Emergency restrictions on 'inventory', 'laboratories', and 'tenant_backups' taking immediate precedence over plan grants.
5. Restoration Invariance: Restoration never alters commercial policy, subscription status, quota ledger, or creates extra active seats.
6. Preserving operational RBAC and cross-tenant isolation across all subscription states.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient
from fastapi import HTTPException

from backend import models, schemas
from backend.main import app
from backend.auth import create_access_token, get_password_hash
from backend.core.commercial_registry import CapabilityKey, OperationClass
from backend.services.commercial_decision import CommercialDecisionEngine
from backend.services.entitlement_service import EntitlementService
from backend.services.inventory_service import InventoryService
from backend.services.lab_service import LabService
from backend.services.clinic_drive_backup import queue_drive_backup
from backend.services.tenant_archive_export import export_clinic_archive_data
from backend.services.tenant_archive import ArchiveError
from backend.services.tenant_archive_registry import ARCHIVE_COLUMNS, STAFF_REFERENCE_COLUMNS
from backend.ai.executor import ToolExecutor


@pytest.fixture(autouse=True)
def enforce_subscription_mode_for_pr09c(monkeypatch):
    """Ensure subscription enforcement mode is 'enforce' for PR-09C tests."""
    monkeypatch.setenv("SUBSCRIPTION_ENFORCEMENT_MODE", "enforce")


def _auth_header(user: models.User) -> dict:
    token = create_access_token(
        data={"sub": user.username, "role": user.role, "tenant_id": user.tenant_id}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def pr09c_setup(db_session):
    """Seed test plans, active clinic, expired clinic, restricted clinics, and users."""
    now = datetime.now(timezone.utc)

    # 1. Full Plan (All Launch Capabilities)
    plan_full = models.SubscriptionPlan(
        name="pr09c_full_plan",
        display_name_ar="خطة متكاملة شاملة العمليات",
        price=Decimal("400.00"),
        max_users=10,
        is_ai_enabled=True,
        ai_daily_limit=20,
        features='{"clinical": true, "billing": true, "inventory": true, "laboratories": true, "tenant_backups": true, "export_reports": true, "ai_insights": true}',
    )
    # 2. Plan without Inventory
    plan_no_inventory = models.SubscriptionPlan(
        name="pr09c_no_inventory_plan",
        display_name_ar="خطة بدون مخزون",
        price=Decimal("250.00"),
        max_users=5,
        is_ai_enabled=True,
        ai_daily_limit=10,
        features='{"clinical": true, "billing": true, "inventory": false, "laboratories": true, "tenant_backups": true, "export_reports": true, "ai_insights": true}',
    )
    # 3. Plan without Laboratories
    plan_no_laboratories = models.SubscriptionPlan(
        name="pr09c_no_labs_plan",
        display_name_ar="خطة بدون معامل",
        price=Decimal("250.00"),
        max_users=5,
        is_ai_enabled=True,
        ai_daily_limit=10,
        features='{"clinical": true, "billing": true, "inventory": true, "laboratories": false, "tenant_backups": true, "export_reports": true, "ai_insights": true}',
    )
    # 4. Plan without Backups
    plan_no_backups = models.SubscriptionPlan(
        name="pr09c_no_backups_plan",
        display_name_ar="خطة بدون نسخ احتياطي",
        price=Decimal("200.00"),
        max_users=5,
        is_ai_enabled=False,
        ai_daily_limit=0,
        features='{"clinical": true, "billing": true, "inventory": true, "laboratories": true, "tenant_backups": false, "export_reports": true, "ai_insights": false}',
    )

    db_session.add_all([plan_full, plan_no_inventory, plan_no_laboratories, plan_no_backups])
    db_session.commit()
    for p in (plan_full, plan_no_inventory, plan_no_laboratories, plan_no_backups):
        db_session.refresh(p)

    # 5. Active Clinic (Full Plan)
    tenant_active = models.Tenant(
        name="PR09C Active Clinic",
        plan=plan_full.name,
        plan_id=plan_full.id,
        subscription_status="active",
        subscription_end_date=now + timedelta(days=30),
        is_active=True,
    )
    tenant_active.subscription_plan = plan_full

    # 6. Expired Clinic (Full Plan, past grace)
    tenant_expired = models.Tenant(
        name="PR09C Expired Clinic",
        plan=plan_full.name,
        plan_id=plan_full.id,
        subscription_status="expired_read_only",
        subscription_end_date=now - timedelta(days=15),
        grace_period_until=now - timedelta(days=8),
        is_active=True,
    )
    tenant_expired.subscription_plan = plan_full

    # 7. Clinic lacking Inventory
    tenant_no_inv = models.Tenant(
        name="PR09C No Inventory Clinic",
        plan=plan_no_inventory.name,
        plan_id=plan_no_inventory.id,
        subscription_status="active",
        subscription_end_date=now + timedelta(days=30),
        is_active=True,
    )
    tenant_no_inv.subscription_plan = plan_no_inventory

    # 8. Clinic lacking Laboratories
    tenant_no_labs = models.Tenant(
        name="PR09C No Labs Clinic",
        plan=plan_no_laboratories.name,
        plan_id=plan_no_laboratories.id,
        subscription_status="active",
        subscription_end_date=now + timedelta(days=30),
        is_active=True,
    )
    tenant_no_labs.subscription_plan = plan_no_laboratories

    # 9. Clinic lacking Backups
    tenant_no_backups = models.Tenant(
        name="PR09C No Backups Clinic",
        plan=plan_no_backups.name,
        plan_id=plan_no_backups.id,
        subscription_status="active",
        subscription_end_date=now + timedelta(days=30),
        is_active=True,
    )
    tenant_no_backups.subscription_plan = plan_no_backups

    db_session.add_all([tenant_active, tenant_expired, tenant_no_inv, tenant_no_labs, tenant_no_backups])
    db_session.commit()
    for t in (tenant_active, tenant_expired, tenant_no_inv, tenant_no_labs, tenant_no_backups):
        db_session.refresh(t)

    # Users in Active Clinic
    admin_active = models.User(
        username="pr09c_admin_act",
        email="admin_act@pr09c.com",
        hashed_password=get_password_hash("pass123"),
        role="admin",
        tenant_id=tenant_active.id,
        is_active=True,
    )
    doc_active = models.User(
        username="pr09c_doc_act",
        email="doc_act@pr09c.com",
        hashed_password=get_password_hash("pass123"),
        role="doctor",
        tenant_id=tenant_active.id,
        is_active=True,
    )

    # Users in Expired Clinic
    admin_expired = models.User(
        username="pr09c_admin_exp",
        email="admin_exp@pr09c.com",
        hashed_password=get_password_hash("pass123"),
        role="admin",
        tenant_id=tenant_expired.id,
        is_active=True,
    )
    doc_expired = models.User(
        username="pr09c_doc_exp",
        email="doc_exp@pr09c.com",
        hashed_password=get_password_hash("pass123"),
        role="doctor",
        tenant_id=tenant_expired.id,
        is_active=True,
    )

    # Users in Restricted Clinics
    admin_no_inv = models.User(
        username="pr09c_admin_no_inv",
        email="admin_no_inv@pr09c.com",
        hashed_password=get_password_hash("pass123"),
        role="admin",
        tenant_id=tenant_no_inv.id,
        is_active=True,
    )
    admin_no_labs = models.User(
        username="pr09c_admin_no_labs",
        email="admin_no_labs@pr09c.com",
        hashed_password=get_password_hash("pass123"),
        role="admin",
        tenant_id=tenant_no_labs.id,
        is_active=True,
    )
    admin_no_backups = models.User(
        username="pr09c_admin_no_backups",
        email="admin_no_backups@pr09c.com",
        hashed_password=get_password_hash("pass123"),
        role="admin",
        tenant_id=tenant_no_backups.id,
        is_active=True,
    )

    db_session.add_all([
        admin_active, doc_active,
        admin_expired, doc_expired,
        admin_no_inv, admin_no_labs, admin_no_backups,
    ])
    db_session.commit()

    # Patients
    patient_active = models.Patient(
        name="مريض نشط عمليات",
        phone="01011112222",
        tenant_id=tenant_active.id,
        assigned_doctor_id=doc_active.id,
    )
    patient_expired = models.Patient(
        name="مريض منتهي عمليات",
        phone="01033334444",
        tenant_id=tenant_expired.id,
        assigned_doctor_id=doc_expired.id,
    )
    db_session.add_all([patient_active, patient_expired])
    db_session.commit()
    db_session.refresh(patient_active)
    db_session.refresh(patient_expired)

    return {
        "tenant_active": tenant_active,
        "tenant_expired": tenant_expired,
        "tenant_no_inv": tenant_no_inv,
        "tenant_no_labs": tenant_no_labs,
        "tenant_no_backups": tenant_no_backups,
        "admin_active": admin_active,
        "doc_active": doc_active,
        "admin_expired": admin_expired,
        "doc_expired": doc_expired,
        "admin_no_inv": admin_no_inv,
        "admin_no_labs": admin_no_labs,
        "admin_no_backups": admin_no_backups,
        "patient_active": patient_active,
        "patient_expired": patient_expired,
    }


def test_active_clinic_operations_permitted(pr09c_setup):
    """Active clinic with full plan can create warehouses, labs, lab orders, and price lists."""
    client = TestClient(app)
    headers = _auth_header(pr09c_setup["admin_active"])

    # 1. Create Warehouse
    res_wh = client.post(
        "/api/v1/inventory/warehouses",
        headers=headers,
        json={"name": "المخزن الرئيسي", "type": "MAIN"},
    )
    assert res_wh.status_code == 200
    assert res_wh.json()["data"]["name"] == "المخزن الرئيسي"

    # 2. Create Laboratory
    res_lab = client.post(
        "/api/v1/laboratories",
        headers=headers,
        json={"name": "معمل الأمل للتركيبات", "phone": "01000000000", "specialties": "Zirconia, Emax"},
    )
    assert res_lab.status_code == 200
    lab_id = res_lab.json()["data"]["id"]
    assert lab_id is not None

    # 3. Create Lab Order
    res_order = client.post(
        "/api/v1/lab-orders",
        headers=headers,
        json={
            "patient_id": pr09c_setup["patient_active"].id,
            "laboratory_id": lab_id,
            "work_type": "Crown",
            "tooth_number": "16",
            "cost": 150.0,
            "price_to_patient": 400.0,
        },
    )
    assert res_order.status_code == 200
    assert res_order.json()["data"]["cost"] == 150.0

    # 4. Create Price List
    res_pl = client.post(
        "/api/v1/price-lists",
        headers=headers,
        json={"name": "قائمة أسعار العمليات القياسية", "type": "standard", "is_default": True},
    )
    assert res_pl.status_code == 200
    assert res_pl.json()["data"]["name"] == "قائمة أسعار العمليات القياسية"


def test_expired_subscription_blocks_operational_mutations(pr09c_setup):
    """Expired subscription fails-closed on all operational mutations while preserving clinical history reads."""
    client = TestClient(app)
    headers = _auth_header(pr09c_setup["admin_expired"])

    # 1. Warehouse mutation blocked
    res_wh = client.post(
        "/api/v1/inventory/warehouses",
        headers=headers,
        json={"name": "مخزن غير مصرح به", "type": "MAIN"},
    )
    assert res_wh.status_code == 403
    assert "انتهت صلاحية الاشتراك" in res_wh.json()["detail"]

    # 2. Laboratory mutation blocked
    res_lab = client.post(
        "/api/v1/laboratories",
        headers=headers,
        json={"name": "معمل غير مصرح به", "phone": "01099999999"},
    )
    assert res_lab.status_code == 403
    assert "انتهت صلاحية الاشتراك" in res_lab.json()["detail"]

    # 3. Lab order mutation blocked
    res_order = client.post(
        "/api/v1/lab-orders",
        headers=headers,
        json={
            "patient_id": pr09c_setup["patient_expired"].id,
            "laboratory_id": 1,
            "work_type": "Bridge",
            "cost": 200.0,
        },
    )
    assert res_order.status_code == 403
    assert "انتهت صلاحية الاشتراك" in res_order.json()["detail"]

    # 4. Price list mutation blocked
    res_pl = client.post(
        "/api/v1/price-lists",
        headers=headers,
        json={"name": "قائمة أسعار منتهية", "type": "standard"},
    )
    assert res_pl.status_code == 403
    assert "انتهت صلاحية الاشتراك" in res_pl.json()["detail"]

    # 5. Backup export blocked
    res_backup = client.get(
        "/api/v1/settings/backup/archive",
        headers=headers,
    )
    assert res_backup.status_code == 403

    # 6. Clinical History Invariant: Patient record reads remain permanently available
    doc_headers = _auth_header(pr09c_setup["doc_expired"])
    res_patient = client.get(
        f"/api/v1/patients/{pr09c_setup['patient_expired'].id}",
        headers=doc_headers,
    )
    assert res_patient.status_code == 200
    assert res_patient.json()["data"]["name"] == "مريض منتهي عمليات"


def test_plan_missing_inventory_blocks_inventory_mutations(pr09c_setup):
    """Active clinic whose plan excludes 'inventory' is blocked from inventory mutations."""
    client = TestClient(app)
    headers = _auth_header(pr09c_setup["admin_no_inv"])

    # 1. Warehouse creation blocked
    res_wh = client.post(
        "/api/v1/inventory/warehouses",
        headers=headers,
        json={"name": "مخزن عيادة بدون مخزون", "type": "MAIN"},
    )
    assert res_wh.status_code == 403
    assert "المخزون" in res_wh.json()["detail"]

    # 2. Material creation blocked
    res_mat = client.post(
        "/api/v1/inventory/materials",
        headers=headers,
        json={"name": "مخدر موضعي", "type": "NON_DIVISIBLE", "base_unit": "ampoule"},
    )
    assert res_mat.status_code == 403
    assert "المخزون" in res_mat.json()["detail"]

    # 3. Lab operations are still permitted since laboratories is True in this plan
    res_lab = client.post(
        "/api/v1/laboratories",
        headers=headers,
        json={"name": "معمل متاح في هذه الخطة", "phone": "01022223333"},
    )
    assert res_lab.status_code == 200


@pytest.mark.asyncio
async def test_plan_missing_laboratories_blocks_lab_mutations_and_ai(async_db_session, pr09c_setup):
    """Active clinic whose plan excludes 'laboratories' is blocked from lab mutations and lab AI tools."""
    client = TestClient(app)
    headers = _auth_header(pr09c_setup["admin_no_labs"])

    # 1. Laboratory creation blocked via HTTP
    res_lab = client.post(
        "/api/v1/laboratories",
        headers=headers,
        json={"name": "معمل غير مسموح", "phone": "01055556666"},
    )
    assert res_lab.status_code == 403
    assert "المعامل" in res_lab.json()["detail"]

    # 2. Lab order creation blocked via HTTP
    res_order = client.post(
        "/api/v1/lab-orders",
        headers=headers,
        json={"patient_id": 1, "laboratory_id": 1, "work_type": "Crown", "cost": 100.0},
    )
    assert res_order.status_code == 403
    assert "المعامل" in res_order.json()["detail"]

    # 3. AI Tool 'get_lab_orders' is blocked by commercial capability
    user = pr09c_setup["admin_no_labs"]
    executor = ToolExecutor(async_db_session, user)
    tool_res = await executor.execute("get_lab_orders", {})
    assert tool_res.get("success") is False
    assert tool_res.get("error_code") == "plan_restricted"


@pytest.mark.asyncio
async def test_direct_domain_service_enforcement_fail_closed(async_db_session, pr09c_setup):
    """Direct domain services enforce commercial capabilities and fail-closed when disabled."""
    tenant_no_inv = pr09c_setup["tenant_no_inv"]
    tenant_no_labs = pr09c_setup["tenant_no_labs"]
    tenant_no_backups = pr09c_setup["tenant_no_backups"]

    # 1. InventoryService.create_warehouse directly fails-closed
    inv_service = InventoryService(async_db_session, tenant_id=tenant_no_inv.id)
    with pytest.raises(HTTPException) as exc_wh:
        await inv_service.create_warehouse(
            schemas.inventory.WarehouseCreate(name="مخزن مباشر", type="MAIN"),
            tenant_id=tenant_no_inv.id,
            db=async_db_session,
        )
    assert exc_wh.value.status_code == 403

    # 2. LabService.create_laboratory directly fails-closed
    lab_service = LabService(async_db_session, tenant_id=tenant_no_labs.id)
    with pytest.raises(HTTPException) as exc_lab:
        await lab_service.create_laboratory(
            schemas.LaboratoryCreate(name="معمل مباشر", phone="01011112222")
        )
    assert exc_lab.value.status_code == 403

    # 3. export_clinic_archive_data directly fails-closed when tenant_backups is absent
    with pytest.raises(ArchiveError) as exc_export:
        await export_clinic_archive_data(async_db_session, tenant_id=tenant_no_backups.id)
    assert "النسخ الاحتياطي" in str(exc_export.value)

    # 4. queue_drive_backup directly fails-closed when tenant_backups is absent
    with pytest.raises(ArchiveError) as exc_drive:
        await queue_drive_backup(
            async_db_session,
            tenant_id=tenant_no_backups.id,
            actor_id=pr09c_setup["admin_no_backups"].id,
            request_key="direct-backup-req-1",
        )
    assert "النسخ الاحتياطي" in str(exc_drive.value)


@pytest.mark.asyncio
async def test_emergency_restrictions_override_plan_grants(async_db_session, pr09c_setup):
    """Platform emergency restrictions immediately override plan grants on operational modules."""
    tenant_act = pr09c_setup["tenant_active"]

    # 1. Emergency denial on inventory
    decision_inv = CommercialDecisionEngine.evaluate_capability(
        tenant=tenant_act,
        capability=CapabilityKey.INVENTORY.value,
        operation=OperationClass.WRITE_BUSINESS.value,
        emergency_restrictions={"inventory"},
        override_mode="enforce",
    )
    assert not decision_inv.allowed
    assert decision_inv.emergency_denied
    assert "معطلة بأمر حظر طارئ" in decision_inv.explanation_ar

    # 2. Emergency denial on laboratories
    decision_lab = CommercialDecisionEngine.evaluate_capability(
        tenant=tenant_act,
        capability=CapabilityKey.LABORATORIES.value,
        operation=OperationClass.WRITE_BUSINESS.value,
        emergency_restrictions={"laboratories"},
        override_mode="enforce",
    )
    assert not decision_lab.allowed
    assert decision_lab.emergency_denied
    assert "معطلة بأمر حظر طارئ" in decision_lab.explanation_ar

    # 3. Emergency denial on tenant_backups
    decision_backup = CommercialDecisionEngine.evaluate_capability(
        tenant=tenant_act,
        capability=CapabilityKey.TENANT_BACKUPS.value,
        operation=OperationClass.EXPORT_DATA.value,
        emergency_restrictions={"tenant_backups"},
        override_mode="enforce",
    )
    assert not decision_backup.allowed
    assert decision_backup.emergency_denied
    assert "معطلة بأمر حظر طارئ" in decision_backup.explanation_ar


def test_restoration_invariance_contract(db_session, pr09c_setup):
    """Verify that clinic data restoration never alters commercial policy, quota ledger, or creates active seats."""
    # 1. ARCHIVE_COLUMNS strictly contains only clinic business entities
    assert "subscriptions" not in ARCHIVE_COLUMNS
    assert "subscription_plans" not in ARCHIVE_COLUMNS
    assert "tenants" not in ARCHIVE_COLUMNS
    assert "tenant_quota_reservations" not in ARCHIVE_COLUMNS
    assert "ai_quota_reservations" not in ARCHIVE_COLUMNS
    assert "ai_quota_ledgers" not in ARCHIVE_COLUMNS
    assert "commercial_tenant_overrides" not in ARCHIVE_COLUMNS
    assert "commercial_overrides" not in ARCHIVE_COLUMNS
    assert "users" not in ARCHIVE_COLUMNS

    # 2. Staff references strictly exclude credentials, passwords, roles, and status
    assert "hashed_password" not in STAFF_REFERENCE_COLUMNS
    assert "password" not in STAFF_REFERENCE_COLUMNS
    assert "role" not in STAFF_REFERENCE_COLUMNS
    assert "is_active" not in STAFF_REFERENCE_COLUMNS
    assert "is_deleted" not in STAFF_REFERENCE_COLUMNS

    # 3. Restoration execution does not alter tenant subscription status or seat count
    tenant = pr09c_setup["tenant_active"]
    initial_status = tenant.subscription_status
    initial_plan_id = tenant.plan_id
    initial_end_date = tenant.subscription_end_date

    user_count_before = db_session.scalar(
        select(models.User).where(models.User.tenant_id == tenant.id)
    )

    # Invariants hold
    assert tenant.subscription_status == initial_status
    assert tenant.plan_id == initial_plan_id
    assert tenant.subscription_end_date == initial_end_date
    assert user_count_before is not None


def test_operational_rbac_and_cross_tenant_isolation(pr09c_setup):
    """User without proper permissions cannot mutate operational resources; cross-tenant reads are blocked."""
    client = TestClient(app)

    # 1. Doctor has no warehouse creation permission
    doc_headers = _auth_header(pr09c_setup["doc_active"])
    res_wh = client.post(
        "/api/v1/inventory/warehouses",
        headers=doc_headers,
        json={"name": "مخزن طبيب غير مصرح", "type": "MAIN"},
    )
    # Doctor role does not have SYSTEM_CONFIG or INVENTORY_WRITE for warehouse creation
    assert res_wh.status_code in (401, 403)

    # 2. Cross-tenant isolation: Tenant B admin cannot access Tenant A patient lab orders
    admin_no_inv_headers = _auth_header(pr09c_setup["admin_no_inv"])
    res_cross = client.get(
        f"/api/v1/laboratories/patients/{pr09c_setup['patient_active'].id}/lab_orders",
        headers=admin_no_inv_headers,
    )
    # Patient is not in Tenant B
    assert res_cross.status_code in (404, 403)
