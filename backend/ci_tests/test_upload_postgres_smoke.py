"""Production-like attachment upload smoke through PostgreSQL and HTTP.

This closes a gap in the staging acceptance path: the cross-tenant suite
covered attachment deletion but did not prove that a normal authenticated
patient upload can be persisted under the restricted NOBYPASSRLS app role.
"""

import os

import httpx
import pytest
from sqlalchemy import select

from backend import auth, models
from backend.database import AsyncSessionLocal, RlsContext
from backend.main import app


TENANT_ID = 99510
USER_ID = 995101
PATIENT_ID = 995102
USERNAME = "pg_upload_smoke_admin"

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00"
)


async def _seed() -> None:
    database_url = os.getenv("DATABASE_URL", "")
    assert database_url.startswith(("postgresql://", "postgres://")), database_url

    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            existing = (
                await db.execute(select(models.Tenant).where(models.Tenant.id == TENANT_ID))
            ).scalars().first()
            if existing is not None:
                return

            db.add(
                models.Tenant(
                    id=TENANT_ID,
                    name="HTTP Upload Smoke Tenant",
                    is_active=True,
                    timezone="Africa/Cairo",
                )
            )
            await db.commit()

    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            db.add(
                models.User(
                    id=USER_ID,
                    username=USERNAME,
                    email="pg-upload-smoke@example.com",
                    hashed_password="not-used-by-jwt-smoke",
                    role="admin",
                    tenant_id=TENANT_ID,
                    is_active=True,
                )
            )
            await db.commit()

    async with AsyncSessionLocal(context=RlsContext(tenant_id=None)) as session:
        async with session.bypass_rls() as db:
            db.add(
                models.Patient(
                    id=PATIENT_ID,
                    name="HTTP Upload Smoke Patient",
                    age=30,
                    phone="01099510102",
                    email=None,
                    medical_history="",
                    notes="upload-smoke",
                    tenant_id=TENANT_ID,
                    assigned_doctor_id=USER_ID,
                    is_deleted=False,
                )
            )
            await db.commit()


@pytest.mark.asyncio
async def test_authenticated_patient_upload_persists_under_postgres(monkeypatch):
    await _seed()

    # The CI contract deliberately exercises the deterministic local fallback.
    # Cloud storage is optional and must never be required for a valid upload.
    for key in (
        "CLOUDINARY_CLOUD_NAME",
        "CLOUDINARY_API_KEY",
        "CLOUDINARY_API_SECRET",
    ):
        monkeypatch.delenv(key, raising=False)

    token = auth.create_access_token(
        data={"sub": USERNAME, "role": "admin", "tenant_id": TENANT_ID}
    )
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        response = await client.post(
            "/api/v1/upload",
            params={"patient_id": PATIENT_ID, "note": "postgres-upload-smoke"},
            files={"file": ("upload-smoke.png", PNG_BYTES, "image/png")},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["patient_id"] == PATIENT_ID
        assert body["file_path"]
        assert body["file_type"] == "image/png"

        stored_path = str(body["file_path"])
        assert stored_path.startswith(f"tenant_{TENANT_ID}/")

        served = await client.get(f"/api/v1/upload/file/{stored_path}")
        assert served.status_code == 200, served.text

    async with AsyncSessionLocal(context=RlsContext(tenant_id=TENANT_ID)) as session:
        persisted = (
            await session.execute(
                select(models.Attachment).where(
                    models.Attachment.patient_id == PATIENT_ID,
                    models.Attachment.file_path == stored_path,
                )
            )
        ).scalars().first()
        assert persisted is not None
