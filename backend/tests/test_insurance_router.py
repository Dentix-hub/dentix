import pytest
from backend.models import InsuranceProvider, PriceList

def test_create_insurance_provider(client, admin_headers, db_session):
    """Test creating an insurance provider and verify default price list creation."""
    payload = {
        "name": "Global Health Insurance",
        "code": "GHI-001",
        "contact_email": "contact@ghi.com"
    }
    response = client.post("/api/v1/insurance-providers/", json=payload, headers=admin_headers)
    
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    data = res["data"]
    assert data["name"] == "Global Health Insurance"
    
    # Verify DB state
    provider = db_session.query(InsuranceProvider).filter(InsuranceProvider.id == data["id"]).first()
    assert provider is not None
    assert provider.name == "Global Health Insurance"
    
    # Verify auto-created price list
    price_list = db_session.query(PriceList).filter(PriceList.insurance_provider_id == provider.id).first()
    assert price_list is not None
    assert price_list.type == "insurance"

def test_get_insurance_providers(client, admin_headers, db_session):
    # Seed a provider
    provider = InsuranceProvider(name="AXA", tenant_id=1, is_active=True)
    db_session.add(provider)
    db_session.commit()
    
    response = client.get("/api/v1/insurance-providers/", headers=admin_headers)
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    data = res["data"]
    assert len(data) >= 1
    assert any(p["name"] == "AXA" for p in data)

def test_update_insurance_provider(client, admin_headers, db_session):
    provider = InsuranceProvider(name="Old Name", tenant_id=1, is_active=True)
    db_session.add(provider)
    db_session.commit()
    
    payload = {"name": "New Name"}
    response = client.put(f"/api/v1/insurance-providers/{provider.id}", json=payload, headers=admin_headers)
    
    assert response.status_code == 200
    db_session.refresh(provider)
    assert provider.name == "New Name"

def test_deactivate_insurance_provider(client, admin_headers, db_session):
    provider = InsuranceProvider(name="To Deactivate", tenant_id=1, is_active=True)
    db_session.add(provider)
    db_session.flush()
    
    # Add a price list
    pl = PriceList(name="Test PL", insurance_provider_id=provider.id, tenant_id=1, is_active=True)
    db_session.add(pl)
    db_session.commit()
    
    response = client.delete(f"/api/v1/insurance-providers/{provider.id}", headers=admin_headers)
    assert response.status_code == 200
    
    db_session.refresh(provider)
    db_session.refresh(pl)
    assert provider.is_active is False
    assert pl.is_active is False
