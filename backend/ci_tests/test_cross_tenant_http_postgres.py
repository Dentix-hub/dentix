"""PostgreSQL HTTP-level tenant-isolation / BOLA closeout gate.

This suite deliberately lives outside backend/tests so the SQLite-forcing
backend/tests/conftest.py cannot replace DATABASE_URL. Requests exercise the
real FastAPI tenant middleware, auth dependency, application AsyncRlsSession,
and PostgreSQL FORCE RLS using a NOBYPASSRLS database role.
"""

from datetime import datetime, timedelta
import os

import httpx
import pytest

from backend import auth, models
from backend.database import AsyncSessionLocal, RlsContext, async_engine
from backend.main import app


TENANT_A = 99465
TENANT_B = 99466
USER_A = 994651
USER_B = 994661
PATIENT_A = 994652
PATIENT_B = 994662
APPOINTMENT_A = 994653
APPOINTMENT_B = 994663
TREATMENT_B = 994664
PAYMENT_A = 994654
PAYMENT_B = 994665
ATTACHMENT_B = 994666
NOTIFICATION_B = 994667
PROCEDURE_B = 994668


def _ids(response: httpx.Response) -> set[int]:
    assert response.status_code == 200, response.text
    body = response.json()
    data = body.get("data", body)
    if isinstance(data, list):
        return {int(item["id"]) for item in data if isinstance(item, dict) and "id" in item}
    return set()


async def _seed_cross_tenant_graph() -> None:
    database_url = os.getenv("DATABASE_URL", "")
    assert database_url.startswith(("postgresql://", "postgres://")), database_url

    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as setup_session:
        async with setup_session.bypass_rls() as db:
            db.add_all(
                [
                    models.Tenant(
                        id=TENANT_A,
                        name="HTTP IDOR Tenant A",
                        is_active=True,
                        timezone="Africa/Cairo",
                    ),
                    models.Tenant(
                        id=TENANT_B,
                        name="HTTP IDOR Tenant B",
                        is_active=True,
                        timezone="Africa/Cairo",
                    ),
                ]
            )
            await db.commit()

    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as setup_session:
        async with setup_session.bypass_rls() as db:
            db.add_all(
                [
                    models.User(
                        id=USER_A,
                        username="pg_http_idor_admin_a",
                        email="pg-http-idor-a@example.com",
                        hashed_password="not-used-by-jwt-test",
                        role="admin",
                        tenant_id=TENANT_A,
                        is_active=True,
                    ),
                    models.User(
                        id=USER_B,
                        username="pg_http_idor_admin_b",
                        email="pg-http-idor-b@example.com",
                        hashed_password="not-used-by-jwt-test",
                        role="admin",
                        tenant_id=TENANT_B,
                        is_active=True,
                    ),
                ]
            )
            await db.commit()

    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as setup_session:
        async with setup_session.bypass_rls() as db:
            db.add_all(
                [
                    models.Patient(
                        id=PATIENT_A,
                        name="Tenant A Control Patient",
                        age=30,
                        phone="01099465001",
                        email=None,
                        medical_history="",
                        notes="tenant-a-control",
                        tenant_id=TENANT_A,
                        assigned_doctor_id=USER_A,
                        is_deleted=False,
                    ),
                    models.Patient(
                        id=PATIENT_B,
                        name="Tenant B Private Patient",
                        age=41,
                        phone="01099466001",
                        email=None,
                        medical_history="",
                        notes="tenant-b-private",
                        tenant_id=TENANT_B,
                        assigned_doctor_id=USER_B,
                        is_deleted=False,
                    ),
                    models.Procedure(
                        id=PROCEDURE_B,
                        name="Tenant B Private Procedure",
                        price=900.0,
                        tenant_id=TENANT_B,
                    ),
                    models.Notification(
                        id=NOTIFICATION_B,
                        title="Tenant B private notification",
                        content="must never be actionable by tenant A",
                        type="info",
                        is_global=False,
                        tenant_id=TENANT_B,
                        created_by_id=USER_B,
                    ),
                ]
            )
            await db.commit()

    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as setup_session:
        async with setup_session.bypass_rls() as db:
            db.add_all(
                [
                    models.Appointment(
                        id=APPOINTMENT_A,
                        patient_id=PATIENT_A,
                        doctor_id=USER_A,
                        date_time=datetime.utcnow() + timedelta(days=3),
                        status="Scheduled",
                        notes="tenant-a-control",
                        tenant_id=TENANT_A,
                        is_deleted=False,
                    ),
                    models.Appointment(
                        id=APPOINTMENT_B,
                        patient_id=PATIENT_B,
                        doctor_id=USER_B,
                        date_time=datetime.utcnow() + timedelta(days=7),
                        status="Scheduled",
                        notes="tenant-b-private",
                        tenant_id=TENANT_B,
                        is_deleted=False,
                    ),
                    models.Treatment(
                        id=TREATMENT_B,
                        patient_id=PATIENT_B,
                        doctor_id=USER_B,
                        tooth_number=11,
                        diagnosis="Private",
                        procedure="Tenant B Procedure",
                        cost=500.0,
                        discount=0.0,
                        status="Done",
                        tenant_id=TENANT_B,
                        is_deleted=False,
                    ),
                    models.Payment(
                        id=PAYMENT_A,
                        patient_id=PATIENT_A,
                        doctor_id=USER_A,
                        amount=100.0,
                        notes="tenant-a-control",
                        tenant_id=TENANT_A,
                    ),
                    models.Payment(
                        id=PAYMENT_B,
                        patient_id=PATIENT_B,
                        doctor_id=USER_B,
                        amount=250.0,
                        notes="tenant-b-private",
                        tenant_id=TENANT_B,
                    ),
                    models.Attachment(
                        id=ATTACHMENT_B,
                        tenant_id=TENANT_B,
                        patient_id=PATIENT_B,
                        file_path=f"tenant_{TENANT_B}/private.txt",
                        filename="private.txt",
                        file_type="text/plain",
                    ),
                ]
            )
            await db.commit()


@pytest.mark.asyncio
async def test_postgres_http_cross_tenant_id_substitution_is_denied():
    await _seed_cross_tenant_graph()

    token = auth.create_access_token(
        data={
            "sub": "pg_http_idor_admin_a",
            "role": "admin",
            "tenant_id": TENANT_A,
        }
    )
    headers = {"Authorization": f"Bearer {token}"}
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers=headers,
    ) as client:
        # Patients: list + detail + mutation.
        patient_list = await client.get("/api/v1/patients")
        patient_ids = _ids(patient_list)
        assert PATIENT_A in patient_ids
        assert PATIENT_B not in patient_ids
        assert (await client.get(f"/api/v1/patients/{PATIENT_B}")).status_code == 404
        assert (
            await client.put(
                f"/api/v1/patients/{PATIENT_B}", json={"notes": "tenant-a-tamper"}
            )
        ).status_code == 404
        assert (await client.delete(f"/api/v1/patients/{PATIENT_B}")).status_code == 404

        # Appointments: list, foreign-patient create, update, status mutation, delete.
        appointment_ids = _ids(await client.get("/api/v1/appointments"))
        assert APPOINTMENT_A in appointment_ids
        assert APPOINTMENT_B not in appointment_ids
        assert (
            await client.post(
                "/api/v1/appointments",
                json={
                    "patient_id": PATIENT_B,
                    "doctor_id": USER_A,
                    "date_time": (datetime.utcnow() + timedelta(days=10)).isoformat(),
                    "status": "Scheduled",
                },
            )
        ).status_code == 404
        assert (
            await client.put(
                f"/api/v1/appointments/{APPOINTMENT_B}",
                json={"notes": "tenant-a-tamper"},
            )
        ).status_code == 404
        assert (
            await client.put(
                f"/api/v1/appointments/{APPOINTMENT_B}/status",
                params={"status": "Completed"},
            )
        ).status_code == 404
        assert (await client.delete(f"/api/v1/appointments/{APPOINTMENT_B}")).status_code == 404

        # Treatments: every ID-addressable route currently exposed by this router.
        treatment_payload = {
            "patient_id": PATIENT_A,
            "tooth_number": 12,
            "diagnosis": "Control",
            "procedure": "Control procedure",
            "cost": 100.0,
            "discount": 0.0,
            "status": "Done",
            "skip_stock_check": True,
        }
        assert (
            await client.put(
                f"/api/v1/treatments/{TREATMENT_B}", json=treatment_payload
            )
        ).status_code == 404
        assert (await client.delete(f"/api/v1/treatments/{TREATMENT_B}")).status_code == 404
        assert (
            await client.get(f"/api/v1/treatments/{TREATMENT_B}/materials")
        ).status_code == 404
        assert (
            await client.post(
                f"/api/v1/treatments/{TREATMENT_B}/materials", json=[]
            )
        ).status_code == 404

        # Payments: list, foreign-patient create, delete.
        payment_ids = _ids(await client.get("/api/v1/payments"))
        assert PAYMENT_A in payment_ids
        assert PAYMENT_B not in payment_ids
        assert (
            await client.post(
                "/api/v1/payments",
                json={"patient_id": PATIENT_B, "amount": 75.0},
            )
        ).status_code == 404
        assert (await client.delete(f"/api/v1/payments/{PAYMENT_B}")).status_code == 404

        # Attachments are patient-owned indirectly; the ID-addressable delete must not cross tenants.
        assert (await client.delete(f"/api/v1/attachments/{ATTACHMENT_B}")).status_code == 404

        # Users/doctors: B user must not appear and cannot be mutated by A admin.
        assert USER_B not in _ids(await client.get("/api/v1/users"))
        assert USER_B not in _ids(await client.get("/api/v1/users/doctors"))
        assert (
            await client.put(
                f"/api/v1/users/{USER_B}", json={"full_name": "Tenant A Tamper"}
            )
        ).status_code == 404
        assert (await client.delete(f"/api/v1/users/{USER_B}")).status_code == 404

        # Notifications have a deliberate global-or-current-tenant RLS policy. A private B row
        # must neither leak into A's list nor accept A's read/dismiss interaction IDs.
        assert NOTIFICATION_B not in _ids(await client.get("/api/v1/notifications"))
        assert (
            await client.post(f"/api/v1/notifications/{NOTIFICATION_B}/read")
        ).status_code == 404
        assert (
            await client.post(f"/api/v1/notifications/{NOTIFICATION_B}/dismiss")
        ).status_code == 404

        # Finance has one ID-addressable analysis endpoint. A tenant-B procedure is missing
        # from tenant A's RLS view and must be surfaced as a normal 404, not a 200 error body.
        assert (
            await client.get(f"/api/v1/financials/procedure/{PROCEDURE_B}/analysis")
        ).status_code == 404
        all_analyses = await client.get("/api/v1/financials/procedures/analysis")
        assert all_analyses.status_code == 200, all_analyses.text
        assert PROCEDURE_B not in {
            int(item["id"])
            for item in all_analyses.json()
            if isinstance(item, dict) and "id" in item
        }

    await async_engine.dispose()
