from backend.database import SessionLocal
from backend import models
from sqlalchemy import text


def test_encryption_verification():
    db = SessionLocal()
    try:
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
        db.add(patient)
        db.commit()
        db.refresh(patient)

        patient_id = patient.id

        # 2. Verify ORM Decryption (Should be plain text)
        print(f"ORM Phone: {patient.phone}")
        assert patient.phone == test_phone

        # 3. Verify Raw SQL Encryption (Should NOT be plain text)
        result = db.execute(
            text("SELECT phone FROM patients WHERE id = :id"), {"id": patient_id}
        ).fetchone()
        raw_phone = result[0]
        print(f"Raw SQL Phone: {raw_phone}")

        assert raw_phone != test_phone
        assert (
            "gAAAA" in raw_phone or len(raw_phone) > 20
        )  # Basic Fernet signature check

        print("SUCCESS: Data is encrypted at rest and decrypted on access.")

        # Cleanup
        db.delete(patient)
        db.commit()

    finally:
        db.close()


if __name__ == "__main__":
    test_encryption_verification()
