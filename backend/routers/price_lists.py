"""
Price Lists Router

CRUD operations for tenant-scoped price lists and pricing.
"""

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.permissions import Permission, require_permission
from backend.core.response import success_response, StandardResponse
from backend.core.tenant_context import require_tenant_id
from backend.database import get_async_db
from ..core.permissions import ADMIN_ROLES
from ..models import InsuranceProvider, PriceList, PriceListItem, Procedure, User
from ..services.pricing_service import get_pricing_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/price-lists", tags=["Price Lists"])


class PriceListCreate(BaseModel):
    name: str
    type: str = "cash"
    description: Optional[str] = None
    is_default: bool = False
    insurance_provider_id: Optional[int] = None
    coverage_percent: float = 100.0
    copay_percent: float = 0.0
    copay_fixed: float = 0.0
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


class PriceListItemCreate(BaseModel):
    procedure_id: int
    price: float
    discount_percent: float = 0.0
    insurance_code: Optional[str] = None
    requires_approval: bool = False


class PriceListResponse(BaseModel):
    id: int
    name: str
    type: str
    is_default: bool
    is_active: bool
    coverage_percent: float
    copay_percent: float

    class Config:
        from_attributes = True


async def _require_visible_procedure(db: AsyncSession, procedure_id: int, tenant_id: int):
    procedure = (
        await db.execute(
            select(Procedure).where(
                Procedure.id == procedure_id,
                or_(Procedure.tenant_id == tenant_id, Procedure.tenant_id.is_(None)),
            )
        )
    ).scalars().first()
    if not procedure:
        raise HTTPException(status_code=404, detail="Procedure not found")
    return procedure


async def _require_insurance_provider(db: AsyncSession, provider_id: int, tenant_id: int):
    provider = (
        await db.execute(
            select(InsuranceProvider).where(
                InsuranceProvider.id == provider_id,
                InsuranceProvider.tenant_id == tenant_id,
                InsuranceProvider.is_active == True,  # noqa: E712
            )
        )
    ).scalars().first()
    if not provider:
        raise HTTPException(status_code=404, detail="Insurance provider not found")
    return provider


@router.get("", response_model=StandardResponse[list])
async def get_price_lists(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    tenant_id = require_tenant_id(current_user)
    pricing = get_pricing_service(db, tenant_id)
    lists = await pricing.get_available_price_lists(current_user)
    return success_response(
        data=[
            {
                "id": pl.id,
                "name": pl.name,
                "type": pl.type,
                "is_default": pl.is_default,
                "is_active": pl.is_active,
            }
            for pl in lists
        ]
    )


@router.get("/default", response_model=StandardResponse[dict])
async def get_default_price_list(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    tenant_id = require_tenant_id(current_user)
    pricing = get_pricing_service(db, tenant_id)
    default = await pricing.get_default_price_list()
    if not default:
        raise HTTPException(status_code=404, detail="No default price list found")
    return success_response(data={"id": default.id, "name": default.name, "type": default.type})


@router.get("/{price_list_id}", response_model=StandardResponse[dict])
async def get_price_list(
    price_list_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    tenant_id = require_tenant_id(current_user)
    try:
        price_list = (
            await db.execute(
                select(PriceList).where(
                    PriceList.id == price_list_id,
                    PriceList.tenant_id == tenant_id,
                )
            )
        ).scalars().first()
        if not price_list:
            raise HTTPException(status_code=404, detail="Price list not found")

        items = (
            await db.execute(
                select(PriceListItem)
                .join(Procedure)
                .where(PriceListItem.price_list_id == price_list_id)
            )
        ).scalars().all()

        return success_response(
            data={
                "id": price_list.id,
                "name": price_list.name,
                "type": price_list.type,
                "is_default": price_list.is_default,
                "is_active": price_list.is_active,
                "coverage_percent": price_list.coverage_percent,
                "copay_percent": price_list.copay_percent,
                "items": [
                    {
                        "id": item.id,
                        "procedure_id": item.procedure_id,
                        "procedure_name": item.procedure.name if item.procedure else None,
                        "price": item.price,
                        "discount_percent": item.discount_percent,
                        "final_price": item.final_price,
                    }
                    for item in items
                ],
            }
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("An exception occurred", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/procedure/{procedure_id}/prices", response_model=StandardResponse[dict])
async def get_procedure_prices(
    procedure_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    tenant_id = require_tenant_id(current_user)
    procedure = await _require_visible_procedure(db, procedure_id, tenant_id)
    pricing = get_pricing_service(db, tenant_id)
    prices = await pricing.get_all_prices_for_procedure(procedure_id)

    return success_response(
        data={
            "procedure_id": procedure_id,
            "procedure_name": procedure.name,
            "legacy_price": procedure.price,
            "price_lists": prices,
        }
    )


@router.post("", response_model=StandardResponse[dict])
async def create_price_list(
    data: PriceListCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    tenant_id = require_tenant_id(current_user)
    if current_user.role not in (ADMIN_ROLES + ["accountant"]):
        raise HTTPException(status_code=403, detail="Admin access required")

    if data.insurance_provider_id is not None:
        await _require_insurance_provider(db, data.insurance_provider_id, tenant_id)

    if data.is_default:
        await db.execute(
            update(PriceList)
            .where(
                PriceList.tenant_id == tenant_id,
                PriceList.is_default == True,  # noqa: E712
            )
            .values(is_default=False)
        )

    price_list = PriceList(
        tenant_id=tenant_id,
        name=data.name,
        type=data.type,
        description=data.description,
        is_default=data.is_default,
        is_active=True,
        insurance_provider_id=data.insurance_provider_id,
        coverage_percent=data.coverage_percent,
        copay_percent=data.copay_percent,
        copay_fixed=data.copay_fixed,
        effective_from=data.effective_from,
        effective_to=data.effective_to,
    )
    db.add(price_list)
    await db.commit()
    await db.refresh(price_list)
    return success_response(data={"id": price_list.id, "name": price_list.name}, message="Created")


@router.post("/{price_list_id}/items", response_model=StandardResponse[dict])
async def add_price_list_item(
    price_list_id: int,
    data: PriceListItemCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    tenant_id = require_tenant_id(current_user)
    if current_user.role not in (ADMIN_ROLES + ["accountant"]):
        raise HTTPException(status_code=403, detail="Admin access required")

    price_list = (
        await db.execute(
            select(PriceList).where(
                PriceList.id == price_list_id,
                PriceList.tenant_id == tenant_id,
            )
        )
    ).scalars().first()
    if not price_list:
        raise HTTPException(status_code=404, detail="Price list not found")

    await _require_visible_procedure(db, data.procedure_id, tenant_id)

    existing = (
        await db.execute(
            select(PriceListItem).where(
                PriceListItem.price_list_id == price_list_id,
                PriceListItem.procedure_id == data.procedure_id,
            )
        )
    ).scalars().first()

    if existing:
        existing.price = data.price
        existing.discount_percent = data.discount_percent
        existing.insurance_code = data.insurance_code
        existing.requires_approval = data.requires_approval
        await db.commit()
        return success_response(data={"id": existing.id}, message="Updated")

    item = PriceListItem(
        price_list_id=price_list_id,
        procedure_id=data.procedure_id,
        price=data.price,
        discount_percent=data.discount_percent,
        insurance_code=data.insurance_code,
        requires_approval=data.requires_approval,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return success_response(data={"id": item.id}, message="Created")


@router.put("/{price_list_id}", response_model=StandardResponse[dict])
async def update_price_list(
    price_list_id: int,
    data: PriceListCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    tenant_id = require_tenant_id(current_user)
    if current_user.role not in (ADMIN_ROLES + ["accountant"]):
        raise HTTPException(status_code=403, detail="Admin access required")

    price_list = (
        await db.execute(
            select(PriceList).where(
                PriceList.id == price_list_id,
                PriceList.tenant_id == tenant_id,
            )
        )
    ).scalars().first()
    if not price_list:
        raise HTTPException(status_code=404, detail="Price list not found")

    if data.insurance_provider_id is not None:
        await _require_insurance_provider(db, data.insurance_provider_id, tenant_id)

    price_list.name = data.name
    price_list.description = data.description
    price_list.coverage_percent = data.coverage_percent
    price_list.copay_percent = data.copay_percent
    price_list.copay_fixed = data.copay_fixed
    price_list.effective_from = data.effective_from
    price_list.effective_to = data.effective_to

    if data.is_default and not price_list.is_default:
        await db.execute(
            update(PriceList)
            .where(
                PriceList.tenant_id == tenant_id,
                PriceList.is_default == True,  # noqa: E712
            )
            .values(is_default=False)
        )
        price_list.is_default = True

    await db.commit()
    return success_response(data={"id": price_list.id}, message="Updated")


@router.delete("/{price_list_id}", response_model=StandardResponse[dict])
async def deactivate_price_list(
    price_list_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    tenant_id = require_tenant_id(current_user)
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required")

    price_list = (
        await db.execute(
            select(PriceList).where(
                PriceList.id == price_list_id,
                PriceList.tenant_id == tenant_id,
            )
        )
    ).scalars().first()
    if not price_list:
        raise HTTPException(status_code=404, detail="Price list not found")

    if price_list.is_default:
        raise HTTPException(status_code=400, detail="Cannot deactivate default price list")

    price_list.is_active = False
    await db.commit()
    return success_response(message="Deactivated")
