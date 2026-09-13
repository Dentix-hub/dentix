"""
Behavior-based tests for ClinicalProjectionCoverage persistence and CRUD.

Validates:
1. Table schema, non-nullable tenant_id, patient_id FK, column defaults.
2. Domain check constraint: ('teeth', 'treatments', 'sessions').
3. Status check constraint: ('UNCOVERED', 'PARTIAL', 'COMPLETE').
4. Unique constraint (tenant_id, patient_id, domain).
5. Default state never implies COMPLETE (defaults to UNCOVERED).
6. CRUD get_projection_coverages and set_projection_coverage methods.
7. Explicit tenant isolation between clinics.
"""

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from backend.models import (
    Base,
    ClinicalProjectionCoverage,
    Patient,
    Tenant,
    User,
)
from backend.models.clinical_core import (
    COVERAGE_DOMAINS,
    COVERAGE_STATES,
    DEFAULT_COVERAGE_STATE,
)
from backend import crud
from backend.core.tenancy import set_current_tenant_id, reset_current_tenant_id


@pytest.fixture(scope="module")
def sqlite_engine():
    engine = sa.create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        t1 = Tenant(id=1, name="Clinic 1")
        t2 = Tenant(id=2, name="Clinic 2")
        session.add_all([t1, t2])
        p1 = Patient(
            id=10,
            tenant_id=1,
            name="Patient 10",
            age=30,
            phone="1234567890",
            medical_history="None",
            notes="",
        )
        p2 = Patient(
            id=20,
            tenant_id=2,
            name="Patient 20",
            age=25,
            phone="0987654321",
            medical_history="None",
            notes="",
        )
        session.add_all([p1, p2])
        session.commit()
    yield engine
    engine.dispose()


def test_coverage_model_constants_and_table_structure():
    """Verify coverage domains, states, and table schema invariants."""
    assert set(COVERAGE_DOMAINS) == {"teeth", "treatments", "sessions"}
    assert set(COVERAGE_STATES) == {"UNCOVERED", "PARTIAL", "COMPLETE"}
    assert DEFAULT_COVERAGE_STATE == "UNCOVERED"

    table = Base.metadata.tables["clinical_projection_coverages"]
    assert table.c.tenant_id.nullable is False
    assert table.c.patient_id.nullable is False
    assert table.c.domain.nullable is False
    assert table.c.status.nullable is False

    # Check constraint names
    ck_names = {c.name for c in table.constraints if isinstance(c, sa.CheckConstraint)}
    assert "ck_cpc_domain" in ck_names
    assert "ck_cpc_status" in ck_names

    # Unique constraint
    uq_constraints = [
        c for c in table.constraints if isinstance(c, sa.UniqueConstraint)
    ]
    uq_cols = [{col.name for col in uq.columns} for uq in uq_constraints]
    assert {"tenant_id", "patient_id", "domain"} in uq_cols


def test_coverage_domain_check_constraint(sqlite_engine):
    """Verify invalid domain raises IntegrityError."""
    with Session(sqlite_engine) as session:
        # Valid domain
        cov = ClinicalProjectionCoverage(
            tenant_id=1,
            patient_id=10,
            domain="teeth",
            status="UNCOVERED",
        )
        session.add(cov)
        session.commit()

        # Invalid domain
        bad_cov = ClinicalProjectionCoverage(
            tenant_id=1,
            patient_id=10,
            domain="invalid_domain",
            status="UNCOVERED",
        )
        session.add(bad_cov)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()


def test_coverage_status_check_constraint(sqlite_engine):
    """Verify invalid status raises IntegrityError."""
    with Session(sqlite_engine) as session:
        bad_status = ClinicalProjectionCoverage(
            tenant_id=1,
            patient_id=10,
            domain="treatments",
            status="INVALID_STATUS",
        )
        session.add(bad_status)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()


def test_coverage_tenant_patient_domain_natural_uniqueness(sqlite_engine):
    """Verify natural uniqueness on (tenant_id, patient_id, domain)."""
    with Session(sqlite_engine) as session:
        # First entry for sessions
        cov1 = ClinicalProjectionCoverage(
            tenant_id=1,
            patient_id=10,
            domain="sessions",
            status="PARTIAL",
        )
        session.add(cov1)
        session.commit()

        # Duplicate (tenant_id=1, patient_id=10, domain="sessions") must fail
        dup = ClinicalProjectionCoverage(
            tenant_id=1,
            patient_id=10,
            domain="sessions",
            status="COMPLETE",
        )
        session.add(dup)
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()
        session.rollback()

        # Different tenant or patient on same domain must succeed
        other_tenant = ClinicalProjectionCoverage(
            tenant_id=2,
            patient_id=20,
            domain="sessions",
            status="COMPLETE",
        )
        session.add(other_tenant)
        session.commit()


@pytest.mark.asyncio
async def test_crud_get_and_set_projection_coverage(sqlite_engine):
    """Verify CRUD methods get_projection_coverages and set_projection_coverage."""
    with Session(sqlite_engine) as session:

        class SessionAdapter:
            def __init__(self, s):
                self._s = s

            async def execute(self, stmt):
                class Result:
                    def __init__(self, res):
                        self._res = res

                    def scalars(self):
                        return self

                    def all(self):
                        return self._res.scalars().all()

                    def first(self):
                        return self._res.scalars().first()

                return Result(self._s.execute(stmt))

            def add(self, obj):
                self._s.add(obj)

            async def flush(self):
                self._s.flush()

        adapted_db = SessionAdapter(session)

        try:
            set_current_tenant_id(1)
            row = await crud.set_projection_coverage(
                adapted_db,
                patient_id=10,
                tenant_id=1,
                domain="teeth",
                status="COMPLETE",
                notes="Fully mapped",
            )
            assert row.status == "COMPLETE"
            assert row.notes == "Fully mapped"

            covs = await crud.get_projection_coverages(
                adapted_db, patient_id=10, tenant_id=1
            )
            assert any(c.domain == "teeth" and c.status == "COMPLETE" for c in covs)

            updated = await crud.set_projection_coverage(
                adapted_db, patient_id=10, tenant_id=1, domain="teeth", status="PARTIAL"
            )
            assert updated.status == "PARTIAL"
        finally:
            reset_current_tenant_id()


@pytest.mark.asyncio
async def test_crud_cross_tenant_isolation_rejection(sqlite_engine):
    """Verify that tenant mismatch raises ValueError."""
    with Session(sqlite_engine) as session:

        class SessionAdapter:
            def __init__(self, s):
                self._s = s

            async def execute(self, stmt):
                return self._s.execute(stmt)

            def add(self, obj):
                self._s.add(obj)

            async def flush(self):
                self._s.flush()

        adapted_db = SessionAdapter(session)

        try:
            set_current_tenant_id(1)
            with pytest.raises(ValueError, match="Tenant Isolation Violation"):
                await crud.get_projection_coverages(
                    adapted_db, patient_id=10, tenant_id=2
                )

            with pytest.raises(ValueError, match="Tenant Isolation Violation"):
                await crud.set_projection_coverage(
                    adapted_db,
                    patient_id=10,
                    tenant_id=2,
                    domain="teeth",
                    status="COMPLETE",
                )
        finally:
            reset_current_tenant_id()
