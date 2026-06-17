"""
Encryption Verification Tests (Async)
Verifies that PII fields are encrypted at rest and decrypted on access.
"""

import pytest
from sqlalchemy import text
from backend import models
from backend.database import Base


@pytest.mark.asyncio
async def test_encryption_verification(async_db_session, async_engine_fixture):
    # Ensure tables exist
    async with async_engine_fixture.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure Tenant exists
    stmt_tenant = await async_db_session.execute(
        models.Tenant.__table__.select().where(models.Tenant.id == 1)
    )
    if not stmt_tenant.first():
        tenant = models.Tenant(id=1, name="Test Clinic", plan="Pro")
        async_db_session.add(tenant)
        await async_db_session.commit()

    # 1. Create a test patient
    test_phone = "01000000000"
    patient = models.Patient(
        name="Encryption Test",
        age=30,
        phone=test_phone,  # Should be encrypted
        medical_history="Secret History",
        notes="Secret Notes",
        tenant_id=1,
    )
    async_db_session.add(patient)
    await async_db_session.commit()
    await async_db_session.refresh(patient)

    patient_id = patient.id

    # 2. Verify ORM Decryption (Should be plain text)
    print(f"ORM Phone: {patient.phone}")
    assert patient.phone == test_phone

    # 3. Verify Raw SQL Encryption (Should NOT be plain text)
    result = await async_db_session.execute(
        text("SELECT phone FROM patients WHERE id = :id"), {"id": patient_id}
    )
    row = result.fetchone()
    raw_phone = row[0]
    print(f"Raw SQL Phone: {raw_phone}")

    assert raw_phone != test_phone
    assert (
        "gAAAA" in raw_phone or len(raw_phone) > 20
    )  # Basic Fernet signature check

    print("SUCCESS: Data is encrypted at rest and decrypted on access.")

    # Cleanup
    await async_db_session.delete(patient)
    await async_db_session.commit()
