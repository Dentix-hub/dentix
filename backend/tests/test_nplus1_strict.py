import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session
from backend import models, schemas
from backend.routers import admin
from backend.services.patient_service import patient_service

@pytest.fixture
def query_counter(db_session):
    class QueryCounter:
        def __init__(self, session):
            self.session = session
            self.count = 0
            self.engine = session.bind

        def __enter__(self):
            self.count = 0
            event.listen(self.engine, "before_cursor_execute", self.callback)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            event.remove(self.engine, "before_cursor_execute", self.callback)

        def callback(self, conn, cursor, statement, parameters, context, executemany):
            self.count += 1
            # print(f"QUERY: {statement}") # Uncomment for debug

    return QueryCounter(db_session)

def test_admin_users_nplus1(db_session, query_counter):
    # 1. Setup Data: 5 tenants, 1 user each
    tenants = []
    for i in range(5):
        t = models.Tenant(name=f"T{i}", plan="trial")
        db_session.add(t)
        tenants.append(t)
    db_session.commit()
    for t in tenants:
        db_session.refresh(t)

    users = []
    for i, t in enumerate(tenants):
        u = models.User(
            username=f"u{i}", 
            hashed_password="pw", 
            role="doctor", 
            tenant_id=t.id
        )
        db_session.add(u)
        users.append(u)
    db_session.commit()

    # 2. Test get_global_users
    # Should be 1 query (or small constant), NOT 1 + N
    admin_user = models.User(role="super_admin")
    
    with query_counter as qc:
        results = admin.get_global_users(db=db_session, limit=100, current_user=admin_user)
        # Access tenant_name to trigger lazy load if any
        names = [r.tenant_name for r in results if isinstance(r, (models.User, schemas.UserAdminView)) or hasattr(r, 'tenant_name')]
    
    # We expect 1 query to fetch users + joined tenants
    # Maybe 1 extra for count?
    # Definitely less than 5 (1 per user)
    print(f"Queries count: {qc.count}")
    assert qc.count < 3, f"Too many queries! {qc.count}"

def test_patients_balance_nplus1(db_session, query_counter):
    # 1. Setup: 1 Tenant, 5 Patients, each with 2 treatments + 2 payments
    t = models.Tenant(name="T_Bal", plan="trial")
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)

    patients = []
    for i in range(5):
        p = models.Patient(name=f"P{i}", tenant_id=t.id)
        db_session.add(p)
        patients.append(p)
    db_session.commit() # Get IDs

    for p in patients:
        # Treatments
        db_session.add(models.Treatment(patient_id=p.id, tenant_id=t.id, cost=100))
        db_session.add(models.Treatment(patient_id=p.id, tenant_id=t.id, cost=200))
        # Payments
        db_session.add(models.Payment(patient_id=p.id, tenant_id=t.id, amount=50))
    db_session.commit()

    # 2. Test get_patients_with_balance
    # Should eager load treatments and payments
    with query_counter as qc:
        debtors = patient_service.get_patients_with_balance(db=db_session, tenant_id=t.id)
        # Logic already ran inside service, so just check count
    
    print(f"Queries count: {qc.count}")
    assert qc.count < 3, f"Too many queries! {qc.count}"
