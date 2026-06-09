"""
N+1 Query Detection Tests

These tests use SQLAlchemy's event system to count the number of SQL queries
executed during common data retrieval patterns. If accessing a list of entities
and their relationships triggers more queries than expected, it signals an
N+1 problem that should be fixed with eager loading (joinedload/selectinload).

Usage:
    pytest backend/tests/test_query_performance.py -v
"""

import pytest
from sqlalchemy import event
from backend.database import SessionLocal, engine


class QueryCounter:
    """Context manager that counts SQL queries executed within its scope."""

    def __init__(self):
        self.count = 0
        self.queries = []

    def __enter__(self):
        event.listen(engine, "before_cursor_execute", self._callback)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        event.remove(engine, "before_cursor_execute", self._callback)

    def _callback(self, conn, cursor, statement, parameters, context, executemany):
        self.count += 1
        # Keep first 200 chars of each query for debugging
        self.queries.append(statement[:200])


# ---------------------------------------------------------------------------
# Patients
# ---------------------------------------------------------------------------

def test_list_patients_no_n_plus_one():
    """
    Listing patients and accessing their scalar columns should NOT trigger
    one query per patient. Budget: 1 main query.
    """
    counter = QueryCounter()
    with counter:
        with SessionLocal() as db:
            from backend.models import Patient
            patients = db.query(Patient).filter(
                Patient.is_deleted == False
            ).limit(20).all()

            # Access scalar columns — these must NOT trigger lazy loads
            for p in patients:
                _ = p.name
                _ = p.tenant_id
                _ = p.created_at

    assert counter.count <= 2, (
        f"Expected ≤ 2 queries for patient list, got {counter.count}.\n"
        f"Queries:\n" + "\n".join(f"  [{i}] {q}" for i, q in enumerate(counter.queries))
    )


def test_list_appointments_with_patient_name():
    """
    Listing appointments and accessing each appointment's patient.name
    is the classic N+1 hotspot. If lazy loading fires, we'll see
    1 + N queries. Budget: ≤ 3 (main + possible joinedload).
    """
    counter = QueryCounter()
    with counter:
        with SessionLocal() as db:
            from backend.models.clinical import Appointment
            from sqlalchemy.orm import joinedload

            appointments = (
                db.query(Appointment)
                .options(joinedload(Appointment.patient))
                .limit(20)
                .all()
            )

            # This is the line that triggers N+1 if patient is lazy-loaded
            for a in appointments:
                if a.patient:
                    _ = a.patient.name

    assert counter.count <= 2, (
        f"Expected ≤ 2 queries for appointments+patient, got {counter.count}.\n"
        f"Queries:\n" + "\n".join(f"  [{i}] {q}" for i, q in enumerate(counter.queries))
    )


def test_list_treatments_with_patient():
    """
    Listing treatments and accessing patient.name should use eager loading.
    """
    counter = QueryCounter()
    with counter:
        with SessionLocal() as db:
            from backend.models.clinical import Treatment
            from sqlalchemy.orm import joinedload

            treatments = (
                db.query(Treatment)
                .options(joinedload(Treatment.patient))
                .limit(20)
                .all()
            )

            for t in treatments:
                if t.patient:
                    _ = t.patient.name

    assert counter.count <= 2, (
        f"Expected ≤ 2 queries for treatments+patient, got {counter.count}.\n"
        f"Queries:\n" + "\n".join(f"  [{i}] {q}" for i, q in enumerate(counter.queries))
    )


def test_list_payments_with_patient():
    """
    Listing payments and accessing patient should not cause N+1.
    """
    counter = QueryCounter()
    with counter:
        with SessionLocal() as db:
            from backend.models.financial import Payment
            from sqlalchemy.orm import joinedload

            payments = (
                db.query(Payment)
                .options(joinedload(Payment.patient))
                .limit(20)
                .all()
            )

            for p in payments:
                if p.patient:
                    _ = p.patient.name

    assert counter.count <= 2, (
        f"Expected ≤ 2 queries for payments+patient, got {counter.count}.\n"
        f"Queries:\n" + "\n".join(f"  [{i}] {q}" for i, q in enumerate(counter.queries))
    )
