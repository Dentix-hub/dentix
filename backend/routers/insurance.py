"""
Insurance Providers Router

CRUD for tenant-scoped insurance companies/providers.
"""

from fastapi import APIRouter, Depends, HTTPException
from backend.core.response import success_response, StandardResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from pydantic import BaseModel
from typing import Optional

from ..models import InsuranceProvider, PriceList, User
from ..core.permissions import Permission, require_permission
from ..core.tenant_context import require_tenant_id
from backend.database import get_async_db

router = APIRouter(prefix="/insurance-providers", tags=["Insurance"])


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


@router.get("", response_model=StandardResponse[list])
async def get_insurance_providers(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    tenant_id = require_tenant_id(current_user)
    providers = (
        await db.execute(
            select(InsuranceProvider).where(
                InsuranceProvider.tenant_id == tenant_id,
                InsuranceProvider.is_active == True,  # noqa: E712
            )
        )
    ).scalars().all()

    result = []
    for provider in providers:
        count = await db.scalar(
            select(func.count(PriceList.id)).where(
                PriceList.insurance_provider_id == provider.id,
                PriceList.tenant_id == tenant_id,
            )
        ) or 0
        result.append(
            {
                "id": provider.id,
                "name": provider.name,
                "code": provider.code,
                "contact_email": provider.contact_email,
                "contact_phone": provider.contact_phone,
                "is_active": provider.is_active,
                "price_lists_count": count,
            }
        )

    return success_response(result)


@router.get("/{provider_id}", response_model=StandardResponse[dict])
async def get_insurance_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    tenant_id = require_tenant_id(current_user)
    provider = (
        await db.execute(
            select(InsuranceProvider).where(
                InsuranceProvider.id == provider_id,
                InsuranceProvider.tenant_id == tenant_id,
            )
        )
    ).scalars().first()

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    price_lists = (
        await db.execute(
            select(PriceList).where(
                PriceList.insurance_provider_id == provider_id,
                PriceList.tenant_id == tenant_id,
            )
        )
    ).scalars().all()

    return success_response(
        {
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
    )


@router.post("", response_model=StandardResponse[dict])
async def create_insurance_provider(
    data: InsuranceProviderCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    tenant_id = require_tenant_id(current_user)
    provider = InsuranceProvider(
        tenant_id=tenant_id,
        name=data.name,
        code=data.code,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        address=data.address,
        notes=data.notes,
        is_active=True,
    )
    db.add(provider)
    await db.flush()

    price_list = PriceList(
        tenant_id=tenant_id,
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
    await db.commit()
    await db.refresh(provider)
    await db.refresh(price_list)

    return success_response(
        {
            "id": provider.id,
            "name": provider.name,
            "price_list_id": price_list.id,
        },
        message="Created",
    )


@router.put("/{provider_id}", response_model=StandardResponse[dict])
async def update_insurance_provider(
    provider_id: int,
    data: InsuranceProviderCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    tenant_id = require_tenant_id(current_user)
    provider = (
        await db.execute(
            select(InsuranceProvider).where(
                InsuranceProvider.id == provider_id,
                InsuranceProvider.tenant_id == tenant_id,
            )
        )
    ).scalars().first()

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    provider.name = data.name
    provider.code = data.code
    provider.contact_email = data.contact_email
    provider.contact_phone = data.contact_phone
    provider.address = data.address
    provider.notes = data.notes

    await db.commit()
    return success_response({"id": provider.id}, message="Updated")


@router.delete("/{provider_id}", response_model=StandardResponse[dict])
async def deactivate_insurance_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    tenant_id = require_tenant_id(current_user)
    provider = (
        await db.execute(
            select(InsuranceProvider).where(
                InsuranceProvider.id == provider_id,
                InsuranceProvider.tenant_id == tenant_id,
            )
        )
    ).scalars().first()

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    res_upd = await db.execute(
        update(PriceList)
        .where(
            PriceList.tenant_id == tenant_id,
            PriceList.insurance_provider_id == provider_id,
            PriceList.is_active == True,  # noqa: E712
        )
        .values(is_active=False)
    )
    deactivated_lists = res_upd.rowcount

    provider.is_active = False
    await db.commit()

    return success_response(
        data={"deactivated_price_lists": deactivated_lists},
        message="Deactivated",
    )
