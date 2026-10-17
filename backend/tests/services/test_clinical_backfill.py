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
from backend.services.clinical_drift_observer_service import ClinicalDriftObserverService
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

    async def test_dry_run_tooth_statuses_and_sessions_writes_nothing(
        self, async_db_session, sample_clinical_extended_data
    ):
        """Dry-run must report would-create counts for tooth statuses and sessions without writing any rows."""
        db = async_db_session

        report = await backfill_tenant(
            db=db,
            tenant_id=1,
            apply=False,
            batch_size=10,
        )

        assert report.is_dry_run is True
        # ToothStatus accounting
        assert report.tooth_statuses_scanned == 4
        assert report.tooth_statuses_created == 2  # ts1 (11), ts2 (12)
        assert report.tooth_statuses_already_synced == 0
        assert report.tooth_statuses_skipped == 2  # ts_invalid_fdi (99), ts_unmapped (14)

        # Session accounting
        assert report.sessions_scanned == 3
        assert report.sessions_created == 2  # sess1 (t101), sess2 (t102)
        assert report.sessions_already_synced == 0
        assert report.sessions_skipped == 1  # sess_deleted (t103 is_deleted=True)

        # Assert no rows were created in ClinicalEvent or CareSession
        ev_ts_count = (
            await db.execute(
                select(func.count(models.ClinicalEvent.id)).where(
                    models.ClinicalEvent.tenant_id == 1
                )
            )
        ).scalar()
        cs_count = (
            await db.execute(
                select(func.count(models.CareSession.id)).where(
                    models.CareSession.tenant_id == 1
                )
            )
        ).scalar()

        assert ev_ts_count == 0
        assert cs_count == 0

    async def test_apply_persists_tooth_status_events_and_care_sessions_with_provenance(
        self, async_db_session, sample_clinical_extended_data
    ):
        """Apply mode persists ClinicalEvent + ClinicalEventTarget and CareSession with provenance (G4-M06, G4-M07)."""
        db = async_db_session

        report = await backfill_tenant(
            db=db,
            tenant_id=1,
            apply=True,
            batch_size=10,
        )

        assert report.is_dry_run is False
        assert report.tooth_statuses_created == 2
        assert report.tooth_statuses_already_synced == 0
        assert report.sessions_created == 2
        assert report.sessions_already_synced == 0

        # Check ClinicalEvents created for legacy tooth statuses (G4-M06)
        ev_res = await db.execute(
            select(models.ClinicalEvent)
            .where(
                models.ClinicalEvent.tenant_id == 1,
                models.ClinicalEvent.work_item_id.is_(None),
            )
            .order_by(models.ClinicalEvent.id.asc())
        )
        ts_events = ev_res.scalars().all()
        assert len(ts_events) == 2

        for ev in ts_events:
            assert ev.event_type in {"finding_recorded", "tooth_lifecycle_changed"}
            assert isinstance(ev.payload, dict)
            assert ev.payload.get("provenance") == "backfill"
            assert ev.payload.get("source") == "legacy_tooth_status"
            assert ev.payload.get("tooth_status_id") in {501, 502}
            assert ev.payload.get("legacy_tooth_status_id") in {501, 502}

        # Check targets for tooth status events
        target_res = await db.execute(
            select(models.clinical_core.ClinicalEventTarget)
            .where(models.clinical_core.ClinicalEventTarget.tenant_id == 1)
            .order_by(models.clinical_core.ClinicalEventTarget.tooth_key.asc())
        )
        targets = target_res.scalars().all()
        # 2 targets for treatment 101 (surfaces M, O) + 1 target for treatment 102 (tooth 21) + 2 targets for tooth status events (11, 12) = 5
        ts_targets = [t for t in targets if t.tooth_key in {"11", "12"}]
        assert len(ts_targets) == 2
        assert {t.tooth_key for t in ts_targets} == {"11", "12"}
        assert all(t.target_kind == "tooth" for t in ts_targets)

        # Check CareSessions created for legacy treatment sessions (G4-M07)
        cs_res = await db.execute(
            select(models.CareSession)
            .where(models.CareSession.tenant_id == 1)
            .order_by(models.CareSession.id.asc())
        )
        care_sessions = cs_res.scalars().all()
        assert len(care_sessions) == 2

        assert care_sessions[0].status == "completed"
        assert "[LEGACY_TREATMENT_SESSION:601]" in care_sessions[0].notes
        assert "Session 1 prep" in care_sessions[0].notes
        assert care_sessions[0].provider_user_id == 10

        assert care_sessions[1].status == "completed"
        assert "[LEGACY_TREATMENT_SESSION:602]" in care_sessions[1].notes
        assert "Session 2 delivery" in care_sessions[1].notes
        assert care_sessions[1].provider_user_id == 10

    async def test_idempotent_apply_twice_creates_no_duplicates_for_ts_and_sessions(
        self, async_db_session, sample_clinical_extended_data
    ):
        """Second apply run produces 0 new tooth status events or care sessions and increments already_synced."""
        db = async_db_session

        # Run 1
        report1 = await backfill_tenant(db=db, tenant_id=1, apply=True)
        assert report1.tooth_statuses_created == 2
        assert report1.tooth_statuses_already_synced == 0
        assert report1.sessions_created == 2
        assert report1.sessions_already_synced == 0

        ev_count_1 = (await db.execute(select(func.count(models.ClinicalEvent.id)))).scalar()
        cs_count_1 = (await db.execute(select(func.count(models.CareSession.id)))).scalar()

        # Run 2
        report2 = await backfill_tenant(db=db, tenant_id=1, apply=True)
        assert report2.tooth_statuses_created == 0
        assert report2.tooth_statuses_already_synced == 2
        assert report2.sessions_created == 0
        assert report2.sessions_already_synced == 2

        ev_count_2 = (await db.execute(select(func.count(models.ClinicalEvent.id)))).scalar()
        cs_count_2 = (await db.execute(select(func.count(models.CareSession.id)))).scalar()

        assert ev_count_2 == ev_count_1
        assert cs_count_2 == cs_count_1

    async def test_tenant_isolation_tooth_statuses_and_sessions(
        self, async_db_session, sample_clinical_extended_data
    ):
        """Backfilling Tenant 1 never creates tooth status events or care sessions for Tenant 2."""
        db = async_db_session

        # Backfill Tenant 1
        await backfill_tenant(db=db, tenant_id=1, apply=True)

        # Verify Tenant 2 has zero events and zero care sessions
        t2_ev_count = (
            await db.execute(
                select(func.count(models.ClinicalEvent.id)).where(
                    models.ClinicalEvent.tenant_id == 2
                )
            )
        ).scalar()
        t2_cs_count = (
            await db.execute(
                select(func.count(models.CareSession.id)).where(
                    models.CareSession.tenant_id == 2
                )
            )
        ).scalar()

        assert t2_ev_count == 0
        assert t2_cs_count == 0

        # Backfill Tenant 2
        report_t2 = await backfill_tenant(db=db, tenant_id=2, apply=True)
        assert report_t2.tooth_statuses_scanned == 1
        assert report_t2.tooth_statuses_created == 1
        assert report_t2.sessions_scanned == 1
        assert report_t2.sessions_created == 1

        t2_cs_after = (
            await db.execute(
                select(func.count(models.CareSession.id)).where(
                    models.CareSession.tenant_id == 2
                )
            )
        ).scalar()
        assert t2_cs_after == 1

    async def test_inventory_and_payment_invariance_g4_m12_g4_m13(
        self, async_db_session, sample_clinical_extended_data
    ):
        """Proves G4-M12 (inventory unchanged) and G4-M13 (payments unchanged) across backfill execution."""
        db = async_db_session

        # Snapshot inventory tables before backfill
        stock_items_before = (
            await db.execute(
                select(models.StockItem.id, models.StockItem.quantity).order_by(models.StockItem.id)
            )
        ).all()
        stock_movements_before = (
            await db.execute(
                select(models.StockMovement.id, models.StockMovement.change_amount).order_by(models.StockMovement.id)
            )
        ).all()
        material_usages_before = (
            await db.execute(
                select(models.TreatmentMaterialUsage.id, models.TreatmentMaterialUsage.quantity_used).order_by(models.TreatmentMaterialUsage.id)
            )
        ).all()

        # Snapshot payment table before backfill
        payments_count_before = (await db.execute(select(func.count(models.Payment.id)))).scalar()
        payments_sum_before = (await db.execute(select(func.sum(models.Payment.amount)))).scalar()
        payments_rows_before = (
            await db.execute(
                select(models.Payment.id, models.Payment.amount, models.Payment.notes).order_by(models.Payment.id)
            )
        ).all()

        # Execute backfill with --apply
        await backfill_tenant(db=db, tenant_id=1, apply=True)

        # Snapshot inventory tables after backfill
        stock_items_after = (
            await db.execute(
                select(models.StockItem.id, models.StockItem.quantity).order_by(models.StockItem.id)
            )
        ).all()
        stock_movements_after = (
            await db.execute(
                select(models.StockMovement.id, models.StockMovement.change_amount).order_by(models.StockMovement.id)
            )
        ).all()
        material_usages_after = (
            await db.execute(
                select(models.TreatmentMaterialUsage.id, models.TreatmentMaterialUsage.quantity_used).order_by(models.TreatmentMaterialUsage.id)
            )
        ).all()

        # Snapshot payment table after backfill
        payments_count_after = (await db.execute(select(func.count(models.Payment.id)))).scalar()
        payments_sum_after = (await db.execute(select(func.sum(models.Payment.amount)))).scalar()
        payments_rows_after = (
            await db.execute(
                select(models.Payment.id, models.Payment.amount, models.Payment.notes).order_by(models.Payment.id)
            )
        ).all()

        # G4-M12: Inventory tables 100% identical
        assert stock_items_after == stock_items_before
        assert stock_movements_after == stock_movements_before
        assert material_usages_after == material_usages_before

        # G4-M13: Payments rows and sum 100% identical
        assert payments_count_after == payments_count_before
        assert payments_sum_after == payments_sum_before
        assert payments_rows_after == payments_rows_before

    async def test_tooth_status_unbackfilled_count_zero_after_apply(
        self, async_db_session
    ):
        """Proves PD01b invariant: tooth_status_unbackfilled_count == 0 on a tenant whose ToothStatus rows all map."""
        db = async_db_session

        # Seed isolated tenant 3 with all-mappable tooth statuses
        t3 = models.Tenant(id=3, name="Clinic Gamma", is_active=True)
        p3 = models.Patient(
            id=30,
            name="Patient Gamma",
            age=40,
            phone="0111111111",
            medical_history="None",
            notes="",
            tenant_id=3,
        )
        ts3_1 = models.ToothStatus(
            id=701, tenant_id=3, patient_id=30, tooth_number=11, condition="Caries", notes="Caries"
        )
        ts3_2 = models.ToothStatus(
            id=702, tenant_id=3, patient_id=30, tooth_number=21, condition="Missing", notes="Missing"
        )
        db.add_all([t3, p3, ts3_1, ts3_2])
        await db.commit()

        # Observer before backfill reports unbackfilled tooth statuses > 0
        observer = ClinicalDriftObserverService(db)
        drift_before = await observer.compute_tenant_drift(tenant_id=3)
        assert drift_before.tooth_status_unbackfilled_count == 2

        # Run backfill with apply
        report = await backfill_tenant(db=db, tenant_id=3, apply=True)
        assert report.tooth_statuses_created == 2

        # Observer after backfill asserts tooth_status_unbackfilled_count == 0
        drift_after = await observer.compute_tenant_drift(tenant_id=3)
        assert drift_after.tooth_status_unbackfilled_count == 0


@pytest.fixture
async def sample_clinical_extended_data(async_db_session, sample_clinical_data):
    """Seed additional tooth statuses, sessions, inventory, and payment records."""
    db = async_db_session

    # ToothStatus for Tenant 1
    ts1 = models.ToothStatus(
        id=501,
        tenant_id=1,
        patient_id=1,
        tooth_number=11,
        condition="Caries",
        notes="Class III Caries",
    )
    ts2 = models.ToothStatus(
        id=502,
        tenant_id=1,
        patient_id=1,
        tooth_number=12,
        condition="Missing",
        notes="Extracted tooth",
    )
    ts_invalid_fdi = models.ToothStatus(
        id=504,
        tenant_id=1,
        patient_id=1,
        tooth_number=99,
        condition="Caries",
        notes="Invalid tooth 99",
    )
    ts_unmapped = models.ToothStatus(
        id=505,
        tenant_id=1,
        patient_id=1,
        tooth_number=14,
        condition="UnknownCondXYZ",
        notes="Unmapped condition",
    )
    # ToothStatus for Tenant 2
    ts_t2 = models.ToothStatus(
        id=506,
        tenant_id=2,
        patient_id=2,
        tooth_number=21,
        condition="Caries",
        notes="Tenant 2 Caries",
    )

    # TreatmentSession for Tenant 1
    sess1 = models.TreatmentSession(
        id=601,
        tenant_id=1,
        treatment_id=101,
        session_date=datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
        notes="Session 1 prep",
    )
    sess2 = models.TreatmentSession(
        id=602,
        tenant_id=1,
        treatment_id=102,
        session_date=datetime(2026, 1, 20, 11, 0, tzinfo=timezone.utc),
        notes="Session 2 delivery",
    )
    sess_deleted = models.TreatmentSession(
        id=603,
        tenant_id=1,
        treatment_id=103,  # Treatment 103 is_deleted=True
        session_date=datetime(2026, 1, 22, 10, 0, tzinfo=timezone.utc),
        notes="Session on deleted treatment 103",
    )
    # TreatmentSession for Tenant 2
    sess_t2 = models.TreatmentSession(
        id=604,
        tenant_id=2,
        treatment_id=201,
        session_date=datetime(2026, 1, 25, 10, 0, tzinfo=timezone.utc),
        notes="Tenant 2 session",
    )

    # Inventory & Financial data for Tenant 1 (G4-M12, G4-M13 invariance testing)
    wh1 = models.Warehouse(id=701, tenant_id=1, name="Main Storage")
    mat1 = models.Material(id=801, tenant_id=1, name="Composite A2", type="DIVISIBLE", base_unit="g")
    batch1 = models.Batch(id=901, tenant_id=1, material_id=801, batch_number="B-100", expiry_date=datetime(2028, 1, 1).date())
    stock1 = models.StockItem(id=1001, tenant_id=1, warehouse_id=701, batch_id=901, quantity=150.0)
    mov1 = models.StockMovement(id=1101, tenant_id=1, stock_item_id=1001, change_amount=-5.0, reason="USAGE")
    usage1 = models.TreatmentMaterialUsage(id=1201, tenant_id=1, treatment_id=101, material_id=801, weight_score=1.0, quantity_used=2.5)

    pay1 = models.Payment(id=1301, tenant_id=1, patient_id=1, amount=300.0, notes="Cash")
    pay2 = models.Payment(id=1302, tenant_id=1, patient_id=1, amount=200.0, notes="Card")

    db.add_all([
        ts1, ts2, ts_invalid_fdi, ts_unmapped, ts_t2,
        sess1, sess2, sess_deleted, sess_t2,
        wh1, mat1, batch1, stock1, mov1, usage1,
        pay1, pay2,
    ])
    await db.commit()

    return {
        **sample_clinical_data,
        "tooth_statuses": [ts1, ts2, ts_invalid_fdi, ts_unmapped, ts_t2],
        "sessions": [sess1, sess2, sess_deleted, sess_t2],
    }

