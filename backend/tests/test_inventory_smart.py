import os
import sys
import pytest
import uuid
from datetime import datetime

# Add project root to sys.path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from backend import models, auth


@pytest.fixture(scope="function")
def test_data(db_session):
    db = db_session
    uid = str(uuid.uuid4())[:8]

    # 1. Create Tenant & User
    tenant = models.Tenant(name=f"Smart Clinic Test {uid}")
    db.add(tenant)
    db.commit()

    password_hash = auth.get_password_hash("testpass")
    username = f"doctor_smart_{uid}"
    user = models.User(
        username=username,
        email=f"doctor_smart_{uid}@example.com",
        hashed_password=password_hash,
        role="doctor",
        tenant_id=tenant.id,
        is_active=True,
    )
    db.add(user)
    db.commit()

    # 2. Create Materials
    mat1 = models.Material(
        name=f"Composite A1 {uid}",
        base_unit="capsule",
        type="NON_DIVISIBLE",
        tenant_id=tenant.id,
    )
    mat2 = models.Material(
        name=f"Bonding Agent {uid}",
        base_unit="ml",
        type="DIVISIBLE",
        tenant_id=tenant.id,
    )
    db.add_all([mat1, mat2])
    db.commit()

    # 3. Create Stock (Availability)
    batch1 = models.Batch(
        material_id=mat1.id,
        batch_number=f"B100_{uid}",
        expiry_date=datetime(2030, 1, 1),
        tenant_id=tenant.id,
    )
    db.add(batch1)
    db.commit()

    stock_item1 = models.StockItem(
        batch_id=batch1.id,
        quantity=50,
        warehouse_id=1,  # Mock ID
        tenant_id=tenant.id,
    )

    warehouse = models.Warehouse(name=f"Main Storage {uid}", tenant_id=tenant.id)
    db.add(warehouse)
    db.commit()
    stock_item1.warehouse_id = warehouse.id
    db.add(stock_item1)
    db.commit()

    # 4. Create Procedure & Weights (Learning)
    proc = models.Procedure(name=f"Filling {uid}", price=100.0, tenant_id=tenant.id)
    db.add(proc)
    db.commit()

    weight1 = models.ProcedureMaterialWeight(
        procedure_id=proc.id,
        material_id=mat1.id,
        weight=2.0,  # Default usage
        sample_size=10,
        current_average_usage=2.5,  # Learning data
        tenant_id=tenant.id,
    )
    db.add(weight1)
    db.commit()

    return {
        "db": db,
        "username": username,
        "procedure": proc,
        "material1": mat1,
        "material2": mat2,
    }


def get_auth_token(db, username):
    user = db.query(models.User).filter_by(username=username).first()
    access_token = auth.create_access_token(
        data={"sub": user.username, "role": user.role, "tenant_id": user.tenant_id}
    )
    return access_token


def test_smart_suggestions(client, test_data):
    """Test fetching intelligent material suggestions for a procedure"""
    db = test_data["db"]
    token = get_auth_token(db, test_data["username"])
    headers = {"Authorization": f"Bearer {token}"}

    proc = test_data["procedure"]

    response = client.get(
        f"/api/v1/inventory/smart/suggestions/{proc.id}", headers=headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    suggestions = data["data"]

    if len(suggestions) >= 1:
        # Check suggestion logic (should prefer current_average_usage if available)
        item = suggestions[0]
        assert item["material"]["name"].startswith("Composite A1")
        assert item["suggested_quantity"] == 2.5  # Matches current_average_usage
        assert item["confidence"] >= 0.9  # High confidence due to sample_size


def test_check_availability(client, test_data):
    """Test pre-flight stock checking"""
    db = test_data["db"]
    token = get_auth_token(db, test_data["username"])
    headers = {"Authorization": f"Bearer {token}"}

    mat1 = test_data["material1"]
    mat2 = test_data["material2"]

    # 1. Check sufficient stock
    payload = {
        "materials": [{"material_id": mat1.id, "quantity": 10}]  # Have 50
    }
    res = client.post(
        "/api/v1/inventory/smart/check-availability", json=payload, headers=headers
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data[0]["status"] == "OK"

    # 2. Check insufficient stock
    payload_high = {
        "materials": [{"material_id": mat1.id, "quantity": 100}]  # Have 50
    }
    res = client.post(
        "/api/v1/inventory/smart/check-availability", json=payload_high, headers=headers
    )
    data = res.json()["data"]
    assert data[0]["status"] == "WARNING"  # or CRITICAL depending on implementation

    # 3. Check out of stock (Mat2 has 0 stock)
    payload_none = {
        "materials": [{"material_id": mat2.id, "quantity": 1}]
    }
    res = client.post(
        "/api/v1/inventory/smart/check-availability", json=payload_none, headers=headers
    )
    data = res.json()["data"]
    assert data[0]["status"] == "CRITICAL"
