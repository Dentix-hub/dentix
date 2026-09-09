"""Real PostgreSQL FORCE-RLS and tenant isolation gate for ClinicalProjectionCoverage."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError

from backend import models
from backend.database import AsyncSessionLocal, RlsContext

TENANT_A = 99581
TENANT_B = 99582
PATIENT_A = 995811
PATIENT_B = 995821
COVERAGE_A = 995812
COVERAGE_B = 995822


async def _seed() -> None:
    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            if await db.get(models.Tenant, TENANT_A) is not None:
                return
            tenant_a = models.Tenant(id=TENANT_A, name="Coverage RLS A")
            tenant_b = models.Tenant(id=TENANT_B, name="Coverage RLS B")
            db.add_all([tenant_a, tenant_b])
            await db.flush()

            patient_a = models.Patient(
                id=PATIENT_A,
                tenant_id=TENANT_A,
                name="Patient Cov A",
                age=30,
                phone="01099581001",
                medical_history="",
                notes="",
            )
            patient_b = models.Patient(
                id=PATIENT_B,
                tenant_id=TENANT_B,
                name="Patient Cov B",
                age=32,
                phone="01099582001",
                medical_history="",
                notes="",
            )
            db.add_all([patient_a, patient_b])
            await db.flush()

            cov_a = models.ClinicalProjectionCoverage(
                id=COVERAGE_A,
                tenant_id=TENANT_A,
                patient_id=PATIENT_A,
                domain="treatments",
                status="COMPLETE",
            )
            cov_b = models.ClinicalProjectionCoverage(
                id=COVERAGE_B,
                tenant_id=TENANT_B,
                patient_id=PATIENT_B,
                domain="treatments",
                status="COMPLETE",
            )
            db.add_all([cov_a, cov_b])
            await db.commit()


@pytest.mark.asyncio
async def test_tenant_a_sees_updates_deletes_only_own_coverage():
    await _seed()
    # 1. Tenant A sees only Tenant A coverage
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_A)) as db:
        res = await db.execute(select(models.ClinicalProjectionCoverage))
        rows = res.scalars().all()
        ids = {r.id for r in rows}
        assert COVERAGE_A in ids
        assert COVERAGE_B not in ids

        # 2. Tenant A cannot see/update Tenant B row
        cov_b = await db.get(models.ClinicalProjectionCoverage, COVERAGE_B)
        assert cov_b is None

        # Tenant A can update own coverage
        cov_a = await db.get(models.ClinicalProjectionCoverage, COVERAGE_A)
        assert cov_a is not None
        cov_a.status = "PARTIAL"
        await db.commit()

    # Re-verify update took effect for Tenant A
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_A)) as db:
        cov_a_updated = await db.get(models.ClinicalProjectionCoverage, COVERAGE_A)
        assert cov_a_updated is not None
        assert cov_a_updated.status == "PARTIAL"

        # 3. Tenant A cannot delete Tenant B row (invisible to Tenant A)
        cov_b = await db.get(models.ClinicalProjectionCoverage, COVERAGE_B)
        assert cov_b is None

        # Tenant A can delete own coverage
        await db.delete(cov_a_updated)
        await db.commit()

    # Verify Tenant A row is gone, Tenant B row is untouched
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_A)) as db:
        assert await db.get(models.ClinicalProjectionCoverage, COVERAGE_A) is None

    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_B)) as db:
        cov_b_check = await db.get(models.ClinicalProjectionCoverage, COVERAGE_B)
        assert cov_b_check is not None
        assert cov_b_check.status == "COMPLETE"


@pytest.mark.asyncio
async def test_cross_tenant_coverage_insert_rejected_by_rls():
    await _seed()
    # Tenant A attempting to insert Tenant B coverage is rejected by FORCE-RLS
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_A)) as db:
        cross_cov = models.ClinicalProjectionCoverage(
            tenant_id=TENANT_B,
            patient_id=PATIENT_B,
            domain="teeth",
            status="UNCOVERED",
        )
        db.add(cross_cov)
        with pytest.raises(DBAPIError):
            await db.commit()
        await db.rollback()


@pytest.mark.asyncio
async def test_natural_tenant_patient_domain_uniqueness_rejects_duplicate():
    await _seed()
    # Duplicate (tenant_id, patient_id, domain) must be rejected by uniqueness constraint
    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_B)) as db:
        dup = models.ClinicalProjectionCoverage(
            tenant_id=TENANT_B,
            patient_id=PATIENT_B,
            domain="treatments",  # COVERAGE_B already covers treatments for PATIENT_B
            status="PARTIAL",
        )
        db.add(dup)
        with pytest.raises((IntegrityError, DBAPIError)):
            await db.commit()
        await db.rollback()
