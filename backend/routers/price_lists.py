"""
Price Lists Router

CRUD operations for price lists and pricing.
"""

import logging
logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends, HTTPException
from backend.core.permissions import Permission, require_permission
from backend.core.response import success_response, StandardResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from typing import Optional
from datetime import date

from ..models import PriceList, PriceListItem, Procedure, User
from ..core.permissions import ADMIN_ROLES
from backend.database import get_async_db
from ..services.pricing_service import get_pricing_service

router = APIRouter(prefix="/price-lists", tags=["Price Lists"])


# --- Schemas ---


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


# --- Endpoints ---


@router.get("", response_model=StandardResponse[list])
async def get_price_lists(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.FINANCIAL_READ)),
):
    """Get available price lists for current user."""
    pricing = get_pricing_service(db, current_user.tenant_id)
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
    """Get default (cash) price list."""
    pricing = get_pricing_service(db, current_user.tenant_id)
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
    """Get a specific price list with items."""
    try:
        stmt_pl = select(PriceList).where(
            PriceList.id == price_list_id,
            PriceList.tenant_id == current_user.tenant_id,
        )
        price_list = (await db.execute(stmt_pl)).scalars().first()

        if not price_list:
            raise HTTPException(status_code=404, detail="Price list not found")

        stmt_items = (
            select(PriceListItem)
            .join(Procedure)
            .where(PriceListItem.price_list_id == price_list_id)
        )
        items = (await db.execute(stmt_items)).scalars().all()

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
    """Get all prices for a procedure across price lists."""
    pricing = get_pricing_service(db, current_user.tenant_id)
    prices = await pricing.get_all_prices_for_procedure(procedure_id)

    # Also get legacy price
    stmt_proc = select(Procedure).where(Procedure.id == procedure_id)
    procedure = (await db.execute(stmt_proc)).scalars().first()
    legacy_price = procedure.price if procedure else 0

    return success_response(
        data={
            "procedure_id": procedure_id,
            "procedure_name": procedure.name if procedure else None,
            "legacy_price": legacy_price,
            "price_lists": prices,
        }
    )


# --- Admin Endpoints ---


@router.post("", response_model=StandardResponse[dict])
async def create_price_list(
    data: PriceListCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Create a new price list (Admin only)."""
    if current_user.role not in (ADMIN_ROLES + ["accountant"]):
        raise HTTPException(status_code=403, detail="Admin access required")

    # If setting as default, unset other defaults
    if data.is_default:
        stmt_upd = (
            update(PriceList)
            .where(
                PriceList.tenant_id == current_user.tenant_id,
                PriceList.is_default == True
            )
            .values(is_default=False)
        )
        await db.execute(stmt_upd)

    price_list = PriceList(
        tenant_id=current_user.tenant_id,
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

    return success_response(
        data={"id": price_list.id, "name": price_list.name}, message="Created"
    )


@router.post("/{price_list_id}/items", response_model=StandardResponse[dict])
async def add_price_list_item(
    price_list_id: int,
    data: PriceListItemCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Add procedure price to a price list (Admin only)."""
    if current_user.role not in (ADMIN_ROLES + ["accountant"]):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Verify price list exists
    stmt_pl = select(PriceList).where(
        PriceList.id == price_list_id,
        PriceList.tenant_id == current_user.tenant_id,
    )
    price_list = (await db.execute(stmt_pl)).scalars().first()

    if not price_list:
        raise HTTPException(status_code=404, detail="Price list not found")

    # Check if item already exists
    stmt_exist = select(PriceListItem).where(
        PriceListItem.price_list_id == price_list_id,
        PriceListItem.procedure_id == data.procedure_id,
    )
    existing = (await db.execute(stmt_exist)).scalars().first()

    if existing:
        # Update existing
        existing.price = data.price
        existing.discount_percent = data.discount_percent
        existing.insurance_code = data.insurance_code
        existing.requires_approval = data.requires_approval
        await db.commit()
        return success_response(data={"id": existing.id}, message="Updated")

    # Create new
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
    """Update a price list (Admin only)."""
    if current_user.role not in (ADMIN_ROLES + ["accountant"]):
        raise HTTPException(status_code=403, detail="Admin access required")

    stmt_pl = select(PriceList).where(
        PriceList.id == price_list_id,
        PriceList.tenant_id == current_user.tenant_id,
    )
    price_list = (await db.execute(stmt_pl)).scalars().first()

    if not price_list:
        raise HTTPException(status_code=404, detail="Price list not found")

    # Update fields
    price_list.name = data.name
    price_list.description = data.description
    price_list.coverage_percent = data.coverage_percent
    price_list.copay_percent = data.copay_percent
    price_list.copay_fixed = data.copay_fixed
    price_list.effective_from = data.effective_from
    price_list.effective_to = data.effective_to

    # Handle default flag
    if data.is_default and not price_list.is_default:
        stmt_upd = (
            update(PriceList)
            .where(
                PriceList.tenant_id == current_user.tenant_id,
                PriceList.is_default == True
            )
            .values(is_default=False)
        )
        await db.execute(stmt_upd)
        price_list.is_default = True

    await db.commit()

    return success_response(data={"id": price_list.id}, message="Updated")


@router.delete("/{price_list_id}", response_model=StandardResponse[dict])
async def deactivate_price_list(
    price_list_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIG)),
):
    """Deactivate a price list (Admin only). Does not delete."""
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required")

    stmt_pl = select(PriceList).where(
        PriceList.id == price_list_id,
        PriceList.tenant_id == current_user.tenant_id,
    )
    price_list = (await db.execute(stmt_pl)).scalars().first()

    if not price_list:
        raise HTTPException(status_code=404, detail="Price list not found")

    if price_list.is_default:
        raise HTTPException(
            status_code=400, detail="Cannot deactivate default price list"
        )

    price_list.is_active = False
    await db.commit()

    return success_response(message="Deactivated")
