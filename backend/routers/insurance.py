"""
Insurance Providers Router

CRUD for insurance companies/providers.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..models import InsuranceProvider, PriceList, User
from ..constants import ROLES
from .auth import get_current_user, get_db

router = APIRouter(prefix="/insurance-providers", tags=["Insurance"])


# --- Schemas ---


class InsuranceProviderCreate(BaseModel):
    name: str
    code: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class InsuranceProviderResponse(BaseModel):
    id: int
    name: str
    code: Optional[str]
    is_active: bool
    price_lists_count: int = 0

    class Config:
        from_attributes = True


# --- Endpoints ---


@router.get("/")
def get_insurance_providers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all insurance providers for tenant."""
    providers = (
        db.query(InsuranceProvider)
        .filter(
            InsuranceProvider.tenant_id == current_user.tenant_id,
            InsuranceProvider.is_active == True,
        )
        .all()
    )

    result = []
    for p in providers:
        # Count price lists
        count = (
            db.query(PriceList).filter(PriceList.insurance_provider_id == p.id).count()
        )

        result.append(
            {
                "id": p.id,
                "name": p.name,
                "code": p.code,
                "contact_email": p.contact_email,
                "contact_phone": p.contact_phone,
                "is_active": p.is_active,
                "price_lists_count": count,
            }
        )

    return result


@router.get("/{provider_id}")
def get_insurance_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific insurance provider."""
    provider = (
        db.query(InsuranceProvider)
        .filter(
            InsuranceProvider.id == provider_id,
            InsuranceProvider.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Get associated price lists
    price_lists = (
        db.query(PriceList).filter(PriceList.insurance_provider_id == provider_id).all()
    )

    return {
        "id": provider.id,
        "name": provider.name,
        "code": provider.code,
        "contact_email": provider.contact_email,
        "contact_phone": provider.contact_phone,
        "address": provider.address,
        "notes": provider.notes,
        "is_active": provider.is_active,
        "price_lists": [
            {"id": pl.id, "name": pl.name, "is_active": pl.is_active}
            for pl in price_lists
        ],
    }


@router.post("/")
def create_insurance_provider(
    data: InsuranceProviderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create insurance provider and a default price list for it (Admin only)."""
    if current_user.role not in ROLES.ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required")

    provider = InsuranceProvider(
        tenant_id=current_user.tenant_id,
        name=data.name,
        code=data.code,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        address=data.address,
        notes=data.notes,
        is_active=True,
    )

    db.add(provider)
    db.flush()  # get provider.id

    # Create a default price list for this provider so it can be assigned to patients
    price_list = PriceList(
        tenant_id=current_user.tenant_id,
        name=data.name,
        type="insurance",
        insurance_provider_id=provider.id,
        is_default=False,
        is_active=True,
        coverage_percent=100.0,
        copay_percent=0.0,
        copay_fixed=0.0,
    )
    db.add(price_list)
    db.commit()
    db.refresh(provider)
    db.refresh(price_list)

    return {
        "id": provider.id,
        "name": provider.name,
        "price_list_id": price_list.id,
        "message": "Created",
    }


@router.put("/{provider_id}")
def update_insurance_provider(
    provider_id: int,
    data: InsuranceProviderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update insurance provider (Admin only)."""
    if current_user.role not in ROLES.ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required")

    provider = (
        db.query(InsuranceProvider)
        .filter(
            InsuranceProvider.id == provider_id,
            InsuranceProvider.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    provider.name = data.name
    provider.code = data.code
    provider.contact_email = data.contact_email
    provider.contact_phone = data.contact_phone
    provider.address = data.address
    provider.notes = data.notes

    db.commit()

    return {"id": provider.id, "message": "Updated"}


@router.delete("/{provider_id}")
def deactivate_insurance_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deactivate insurance provider (Admin only)."""
    if current_user.role not in ROLES.ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required")

    provider = (
        db.query(InsuranceProvider)
        .filter(
            InsuranceProvider.id == provider_id,
            InsuranceProvider.tenant_id == current_user.tenant_id,
        )
        .first()
    )

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Deactivate associated price lists (soft delete) so provider can be deactivated.
    deactivated_lists = (
        db.query(PriceList)
        .filter(
            PriceList.tenant_id == current_user.tenant_id,
            PriceList.insurance_provider_id == provider_id,
            PriceList.is_active == True,
        )
        .update({"is_active": False})
    )

    provider.is_active = False
    db.commit()

    return {"message": "Deactivated", "deactivated_price_lists": deactivated_lists}
