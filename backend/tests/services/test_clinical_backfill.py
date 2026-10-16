"""
Tests for G4 Controlled Backfill CLI (scripts/backfill_clinical_work_items.py).

Verifies:
1. Dry-run mode writes nothing to the database.
2. Apply mode persists ClinicalWorkItem, ClinicalWorkItemTarget, and ClinicalEvent with provenance.
3. Idempotency: running apply twice produces identical records without duplicates.
4. Tenant isolation: backfilling Tenant A never touches or creates items for Tenant B.
5. Skip reasons: soft-deleted, missing tooth number, and invalid FDI notation are categorized and skipped.
6. Resumability & batching: processes across batches and resumes accurately with after-id.
7. Legacy Treatment invariance: Treatment rows are never mutated or updated.

Note on environment: verified against SQLite (in-memory async fixture); PostgreSQL RLS enforcement
is covered by backend/ci_tests.
"""

from datetime import datetime, timezone
import pytest
from sqlalchemy import select, func

from backend import models
from scripts.backfill_clinical_work_items import (
    backfill_tenant,
    discover_active_tenants,
    TenantBackfillReport,
)


@pytest.fixture
async def sample_clinical_data(async_db_session):
    """Seed test tenants, users, patients, and treatments."""
    db = async_db_session

    # Tenants
    t1 = models.Tenant(id=1, name="Clinic Alpha", is_active=True)
    t2 = models.Tenant(id=2, name="Clinic Beta", is_active=True)
    db.add_all([t1, t2])
    await db.flush()

    # Users
    u1 = models.User(id=10, username="dr_alpha", email="dr_alpha@example.com", hashed_password="fakehash", tenant_id=1, role="doctor")
    u2 = models.User(id=20, username="dr_beta", email="dr_beta@example.com", hashed_password="fakehash", tenant_id=2, role="doctor")
    db.add_all([u1, u2])
    await db.flush()

    # Patients
    p1 = models.Patient(id=1, name="Patient 1", age=30, phone="0123456789", medical_history="None", notes="", tenant_id=1)
    p2 = models.Patient(id=2, name="Patient 2", age=30, phone="0123456788", medical_history="None", notes="", tenant_id=2)
    db.add_all([p1, p2])
    await db.flush()

    # Treatments for Tenant 1
    # 1. Valid treatment 1 on tooth 16
    t1_1 = models.Treatment(
        id=101,
        tenant_id=1,
        patient_id=1,
        tooth_number=16,
        procedure="Composite Filling",
        status="Done",
        cost=500.0,
        doctor_id=10,
        notes="Class I [Surfaces: M, O]",
    )
    # 2. Valid treatment 2 on tooth 21
    t1_2 = models.Treatment(
        id=102,
        tenant_id=1,
        patient_id=1,
        tooth_number=21,
        procedure="Crown",
        status="Pending",
        cost=1500.0,
        doctor_id=10,
        notes="Porcelain crown",
    )
    # 3. Soft-deleted treatment (should be skipped)
    t1_deleted = models.Treatment(
        id=103,
        tenant_id=1,
        patient_id=1,
        tooth_number=36,
        procedure="Extraction",
        status="Done",
        cost=300.0,
        doctor_id=10,
        is_deleted=True,
    )
    # 4. Missing tooth number (should be skipped)
    t1_no_tooth = models.Treatment(
        id=104,
        tenant_id=1,
        patient_id=1,
        tooth_number=None,
        procedure="Examination",
        status="Done",
        cost=100.0,
        doctor_id=10,
    )
    # 5. Invalid FDI tooth number (99) (should be skipped)
    t1_invalid_fdi = models.Treatment(
        id=105,
        tenant_id=1,
        patient_id=1,
        tooth_number=99,
        procedure="Scaling",
        status="Done",
        cost=200.0,
        doctor_id=10,
    )
    # 6. Unmapped procedure on valid FDI tooth (should be skipped as unmapped)
    t1_unmapped = models.Treatment(
        id=106,
        tenant_id=1,
        patient_id=1,
        tooth_number=14,
        procedure="Unmapped Custom Procedure",
        status="Done",
        cost=250.0,
        doctor_id=10,
    )

    # Treatment for Tenant 2
    t2_1 = models.Treatment(
        id=201,
        tenant_id=2,
        patient_id=2,
        tooth_number=46,
        procedure="Root Canal",
        status="Done",
        cost=2000.0,
        doctor_id=20,
    )

    db.add_all([t1_1, t1_2, t1_deleted, t1_no_tooth, t1_invalid_fdi, t1_unmapped, t2_1])
    await db.commit()

    return {
        "tenant_1_treatments": [t1_1, t1_2, t1_deleted, t1_no_tooth, t1_invalid_fdi, t1_unmapped],
        "tenant_2_treatments": [t2_1],
    }


class TestClinicalBackfillCLI:
    """Test suite for controlled G4 treatment backfill."""

    async def test_dry_run_writes_nothing(self, async_db_session, sample_clinical_data):
        """Dry-run must report would-create counts without inserting any database rows."""
        db = async_db_session

        report = await backfill_tenant(
            db=db,
            tenant_id=1,
            apply=False,
            batch_size=10,
        )

        assert report.is_dry_run is True
        assert report.scanned == 6
        assert report.created == 2  # Would create 101, 102
        assert report.already_synced == 0
        assert report.total_skipped == 4
        assert report.skipped_soft_deleted == 1
        assert report.skipped_missing_tooth == 1
        assert report.skipped_invalid_fdi == 1
        assert report.skipped_unmapped == 1

        # Assert no rows were created in ClinicalWorkItem or ClinicalEvent
        wi_count = (await db.execute(select(func.count(models.ClinicalWorkItem.id)))).scalar()
        ev_count = (await db.execute(select(func.count(models.ClinicalEvent.id)))).scalar()
        target_count = (await db.execute(select(func.count(models.ClinicalWorkItemTarget.id)))).scalar()

        assert wi_count == 0
        assert ev_count == 0
        assert target_count == 0

    async def test_apply_persists_work_items_and_events_with_provenance(
        self, async_db_session, sample_clinical_data
    ):
        """Apply mode creates ClinicalWorkItem, ClinicalWorkItemTarget, and ClinicalEvent with provenance."""
        db = async_db_session

        report = await backfill_tenant(
            db=db,
            tenant_id=1,
            apply=True,
            batch_size=10,
        )

        assert report.is_dry_run is False
        assert report.scanned == 6
        assert report.created == 2
        assert report.already_synced == 0

        # Assert exactly 2 work items created for Tenant 1
        res = await db.execute(
            select(models.ClinicalWorkItem)
            .where(models.ClinicalWorkItem.tenant_id == 1)
            .order_by(models.ClinicalWorkItem.id.asc())
        )
        work_items = res.scalars().all()
        assert len(work_items) == 2

        # Check work item 1 (from Treatment 101: tooth 16, Composite Filling, Done)
        wi1 = work_items[0]
        assert wi1.code == "REST_COMPOSITE"
        assert wi1.status == "completed"
        assert wi1.patient_id == 1
        assert wi1.created_by_user_id == 10

        # Check targets for work item 1 (surfaces M, O)
        targets_res = await db.execute(
            select(models.ClinicalWorkItemTarget)
            .where(models.ClinicalWorkItemTarget.work_item_id == wi1.id)
            .order_by(models.ClinicalWorkItemTarget.surface_code.asc())
        )
        targets = targets_res.scalars().all()
        assert len(targets) == 2
        assert {t.surface_code for t in targets} == {"M", "O"}
        assert all(t.tooth_key == "16" for t in targets)
        assert all(t.target_kind == "surface" for t in targets)

        # Check work item 2 (from Treatment 102: tooth 21, Crown, Pending)
        wi2 = work_items[1]
        assert wi2.code == "PROS_CROWN"
        assert wi2.status == "planned"

        # Check ClinicalEvents and Option A provenance tag
        ev_res = await db.execute(
            select(models.ClinicalEvent)
            .where(models.ClinicalEvent.tenant_id == 1)
            .order_by(models.ClinicalEvent.id.asc())
        )
        events = ev_res.scalars().all()
        assert len(events) == 2

        for ev in events:
            assert ev.event_type == "procedure_recorded"
            assert isinstance(ev.payload, dict)
            # Option A provenance verification
            assert ev.payload.get("provenance") == "backfill"
            assert ev.payload.get("source") == "legacy_treatment"
            assert "treatment_id" in ev.payload

    async def test_idempotent_apply_twice_creates_no_duplicates(
        self, async_db_session, sample_clinical_data
    ):
        """Re-running backfill with apply produces zero duplicates and marks all existing rows as already_synced."""
        db = async_db_session

        # First run (Apply)
        report1 = await backfill_tenant(db=db, tenant_id=1, apply=True)
        assert report1.created == 2
        assert report1.already_synced == 0

        # Capture counts after first run
        wi_count_1 = (await db.execute(select(func.count(models.ClinicalWorkItem.id)))).scalar()
        ev_count_1 = (await db.execute(select(func.count(models.ClinicalEvent.id)))).scalar()
        target_count_1 = (await db.execute(select(func.count(models.ClinicalWorkItemTarget.id)))).scalar()

        # Second run (Apply again)
        report2 = await backfill_tenant(db=db, tenant_id=1, apply=True)
        assert report2.created == 0
        assert report2.already_synced == 2
        assert report2.scanned == 6

        # Counts must be completely unchanged
        wi_count_2 = (await db.execute(select(func.count(models.ClinicalWorkItem.id)))).scalar()
        ev_count_2 = (await db.execute(select(func.count(models.ClinicalEvent.id)))).scalar()
        target_count_2 = (await db.execute(select(func.count(models.ClinicalWorkItemTarget.id)))).scalar()

        assert wi_count_2 == wi_count_1
        assert ev_count_2 == ev_count_1
        assert target_count_2 == target_count_1

    async def test_tenant_isolation(self, async_db_session, sample_clinical_data):
        """Backfilling Tenant 1 must never touch, scan, or create records for Tenant 2."""
        db = async_db_session

        # Run backfill for Tenant 1 only
        report = await backfill_tenant(db=db, tenant_id=1, apply=True)
        assert report.created == 2

        # Verify Tenant 2 has zero work items and zero events
        t2_wi_count = (
            await db.execute(
                select(func.count(models.ClinicalWorkItem.id)).where(
                    models.ClinicalWorkItem.tenant_id == 2
                )
            )
        ).scalar()
        t2_ev_count = (
            await db.execute(
                select(func.count(models.ClinicalEvent.id)).where(
                    models.ClinicalEvent.tenant_id == 2
                )
            )
        ).scalar()

        assert t2_wi_count == 0
        assert t2_ev_count == 0

        # Now backfill Tenant 2
        report2 = await backfill_tenant(db=db, tenant_id=2, apply=True)
        assert report2.scanned == 1
        assert report2.created == 1
        assert report2.already_synced == 0

        t2_wi_count_after = (
            await db.execute(
                select(func.count(models.ClinicalWorkItem.id)).where(
                    models.ClinicalWorkItem.tenant_id == 2
                )
            )
        ).scalar()
        assert t2_wi_count_after == 1

    async def test_skip_reasons(self, async_db_session, sample_clinical_data):
        """All invalid/ineligible treatments must be accurately counted by skip reason."""
        db = async_db_session

        report = await backfill_tenant(db=db, tenant_id=1, apply=False)

        assert report.scanned == 6
        assert report.skipped_soft_deleted == 1  # Treatment 103 (is_deleted=True)
        assert report.skipped_missing_tooth == 1  # Treatment 104 (tooth_number=None)
        assert report.skipped_invalid_fdi == 1   # Treatment 105 (tooth_number=99)
        assert report.skipped_unmapped == 1      # Treatment 106 (procedure="Unmapped Custom Procedure")
        assert report.total_skipped == 4

    async def test_batched_execution_and_resumability(
        self, async_db_session, sample_clinical_data
    ):
        """Chunked processing across small batch sizes and resumption with after_id."""
        db = async_db_session

        # 1. Process in small batches of 2
        report = await backfill_tenant(
            db=db,
            tenant_id=1,
            apply=True,
            batch_size=2,
            after_id=0,
        )
        assert report.batch_count == 3  # 6 treatments across batch size 2 -> 2 + 2 + 2
        assert report.scanned == 6
        assert report.created == 2

        # 2. Test after_id parameter: resuming after treatment 102
        report_resumed = await backfill_tenant(
            db=db,
            tenant_id=1,
            apply=False,
            after_id=102,
        )
        # Treatments > 102 are 103 (deleted), 104 (no tooth), 105 (invalid fdi), 106 (unmapped)
        assert report_resumed.scanned == 4
        assert report_resumed.created == 0
        assert report_resumed.total_skipped == 4

    async def test_legacy_treatments_unmodified(
        self, async_db_session, sample_clinical_data
    ):
        """Legacy treatment rows must never be updated, deleted, or mutated."""
        db = async_db_session

        # Read treatment snapshot before backfill
        before_res = await db.execute(
            select(models.Treatment)
            .where(models.Treatment.tenant_id == 1)
            .execution_options(include_deleted=True)
            .order_by(models.Treatment.id.asc())
        )
        treatments_before = [
            (t.id, t.procedure, t.status, t.cost, t.notes, t.tooth_number, t.is_deleted)
            for t in before_res.scalars().all()
        ]

        # Execute backfill with apply
        await backfill_tenant(db=db, tenant_id=1, apply=True)

        # Read treatment snapshot after backfill
        after_res = await db.execute(
            select(models.Treatment)
            .where(models.Treatment.tenant_id == 1)
            .execution_options(include_deleted=True)
            .order_by(models.Treatment.id.asc())
        )
        treatments_after = [
            (t.id, t.procedure, t.status, t.cost, t.notes, t.tooth_number, t.is_deleted)
            for t in after_res.scalars().all()
        ]

        # Exact match required
        assert treatments_after == treatments_before

    async def test_discover_active_tenants_excludes_inactive_and_deleted(
        self, async_db_session, sample_clinical_data
    ):
        """discover_active_tenants must return only active, non-deleted tenants."""
        db = async_db_session
        t_inactive = models.Tenant(id=3, name="Clinic Inactive", is_active=False)
        t_deleted = models.Tenant(id=4, name="Clinic Deleted", is_active=True, is_deleted=True)
        db.add_all([t_inactive, t_deleted])
        await db.commit()

        active_ids = await discover_active_tenants(db)
        assert active_ids == [1, 2]

