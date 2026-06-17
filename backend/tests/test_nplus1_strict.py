import pytest
from sqlalchemy import select, event
from backend import models, schemas
from backend.routers import admin_system
from backend.services.patient_service import patient_service
from backend.database import Base


@pytest.fixture(autouse=True)
async def setup_tables(async_engine_fixture):
    async with async_engine_fixture.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
def query_counter(async_db_session):
    class QueryCounter:
        def __init__(self, session):
            self.session = session
            self.count = 0
            self.engine = session.bind.sync_engine

        def __enter__(self):
            self.count = 0
            event.listen(self.engine, "before_cursor_execute", self.callback)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            event.remove(self.engine, "before_cursor_execute", self.callback)

        def callback(self, conn, cursor, statement, parameters, context, executemany):
            self.count += 1

    return QueryCounter(async_db_session)


@pytest.mark.anyio
async def test_admin_users_nplus1(async_db_session, query_counter):
    # 1. Setup Data: 5 tenants, 1 user each
    tenants = []
    for i in range(5):
        t = models.Tenant(name=f"T{i}", plan="trial")
        async_db_session.add(t)
        tenants.append(t)
    await async_db_session.commit()
    for t in tenants:
        await async_db_session.refresh(t)

    users = []
    for i, t in enumerate(tenants):
        u = models.User(
            username=f"u{i}",
            email=f"u{i}@example.com",
            hashed_password="pw",
            role="doctor",
            tenant_id=t.id
        )
        async_db_session.add(u)
        users.append(u)
    await async_db_session.commit()

    # 2. Test get_global_users
    admin_user = models.User(role="super_admin")

    with query_counter as qc:
        results = await admin_system.get_global_users(db=async_db_session, limit=100, current_user=admin_user)
        [r.tenant_name for r in results if isinstance(r, (models.User, schemas.UserAdminView)) or hasattr(r, 'tenant_name')]

    print(f"Queries count: {qc.count}")
    assert qc.count < 3, f"Too many queries! {qc.count}"


@pytest.mark.anyio
async def test_patients_balance_nplus1(async_db_session, query_counter):
    # 1. Setup: 1 Tenant, 5 Patients, each with 2 treatments + 2 payments
    t = models.Tenant(name="T_Bal", plan="trial")
    async_db_session.add(t)
    await async_db_session.commit()
    await async_db_session.refresh(t)

    patients = []
    for i in range(5):
        p = models.Patient(name=f"P{i}", tenant_id=t.id, age=30, phone=f"011111111{i}", medical_history="", notes="")
        async_db_session.add(p)
        patients.append(p)
    await async_db_session.commit()

    for p in patients:
        await async_db_session.refresh(p)
        # Treatments
        async_db_session.add(models.Treatment(patient_id=p.id, tenant_id=t.id, cost=100, procedure="T1"))
        async_db_session.add(models.Treatment(patient_id=p.id, tenant_id=t.id, cost=200, procedure="T2"))
        # Payments
        async_db_session.add(models.Payment(patient_id=p.id, tenant_id=t.id, amount=50))
    await async_db_session.commit()

    # 2. Test get_patients_with_balance
    with query_counter as qc:
        await patient_service.get_patients_with_balance(db=async_db_session, tenant_id=t.id)

    print(f"Queries count: {qc.count}")
    assert qc.count < 3, f"Too many queries! {qc.count}"
