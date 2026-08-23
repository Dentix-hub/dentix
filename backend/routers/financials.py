import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend import schemas
from backend.core.permissions import Permission, require_permission
from backend.core.response import StandardResponse, success_response
from backend.core.tenant_context import require_tenant_id
from backend.database import get_async_db
from backend.services.cost_engine import CostEngine
from backend.services.finance_report_service import build_csv_document

router = APIRouter(prefix="/financials", tags=["Financials"])
logger = logging.getLogger("smart_clinic")


@router.get("/procedure/{procedure_id}/analysis")
async def analyze_procedure_cost(
    procedure_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.REPORT_READ)),
):
    """Get detailed material-cost breakdown for a tenant-visible procedure."""
    tenant_id = require_tenant_id(current_user)
    engine = CostEngine(db, tenant_id)
    try:
        analysis = await engine.calculate_procedure_cost(procedure_id)
        if analysis.get("error") == "Procedure not found":
            raise HTTPException(status_code=404, detail="Procedure not found")
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Procedure cost analysis error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to calculate procedure cost") from e


@router.get("/procedures/analysis")
async def analyze_all_procedures_cost(
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.REPORT_READ)),
):
    """Compatibility bulk material-cost analysis with reliability metadata."""
    tenant_id = require_tenant_id(current_user)
    engine = CostEngine(db, tenant_id)
    try:
        return await engine.calculate_all_procedures_costs()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Bulk analysis error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to calculate bulk analysis") from e


@router.get("/reports/material-margin", response_model=StandardResponse[dict])
async def get_material_margin_report(
    search: Optional[str] = Query(None, max_length=200),
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    sort: str = Query("name_asc", pattern="^(name|price)_(asc|desc)$"),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.REPORT_READ)),
):
    """Paginated estimated material-margin report with evidence completeness."""
    tenant_id = require_tenant_id(current_user)
    engine = CostEngine(db, tenant_id)
    data = await engine.calculate_material_margin_report(
        search=search,
        skip=skip,
        limit=limit,
        sort=sort,
    )
    return success_response(data=data, message="Material margin report retrieved successfully")


@router.get("/reports/material-margin/export.csv")
async def export_material_margin_report_csv(
    search: Optional[str] = Query(None, max_length=200),
    sort: str = Query("name_asc", pattern="^(name|price)_(asc|desc)$"),
    locale: str = Query("en", pattern="^(ar|en)$"),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.REPORT_EXPORT)),
):
    """Export the full active-filter result set, batching analysis on the server."""
    tenant_id = require_tenant_id(current_user)
    engine = CostEngine(db, tenant_id)

    rows = []
    skip = 0
    batch_size = 100
    total = None
    completeness = {"complete": 0, "partial": 0, "unavailable": 0, "errors": 0}

    while total is None or skip < total:
        page = await engine.calculate_material_margin_report(
            search=search,
            skip=skip,
            limit=batch_size,
            sort=sort,
        )
        pagination = page.get("pagination", {})
        total = int(pagination.get("total", 0))
        page_items = page.get("items", [])
        rows.extend(page_items)
        page_completeness = page.get("completeness", {})
        for key in completeness:
            completeness[key] += int(page_completeness.get(key, 0) or 0)
        if not page_items:
            break
        skip += len(page_items)

    labels = {
        "en": {
            "procedure": "Procedure",
            "price": "Current price",
            "material_cost": "Estimated material cost",
            "margin": "Estimated material margin",
            "margin_percent": "Margin %",
            "coverage": "Coverage %",
            "confidence": "Confidence",
            "status": "Status",
            "definition": "Definition version",
            "scope": "Metric scope",
            "filter": "Search filter",
            "complete": "Complete rows",
            "partial": "Partial rows",
            "unavailable": "Unavailable rows",
            "errors": "Error rows",
        },
        "ar": {
            "procedure": "الإجراء",
            "price": "السعر الحالي",
            "material_cost": "تكلفة المواد التقديرية",
            "margin": "هامش المواد التقديري",
            "margin_percent": "نسبة الهامش %",
            "coverage": "نسبة الاكتمال %",
            "confidence": "الثقة",
            "status": "الحالة",
            "definition": "إصدار التعريف",
            "scope": "نطاق المؤشر",
            "filter": "فلتر البحث",
            "complete": "صفوف مكتملة",
            "partial": "صفوف جزئية",
            "unavailable": "صفوف غير متاحة",
            "errors": "صفوف بها خطأ",
        },
    }[locale]

    csv_text = build_csv_document(
        columns=[
            ("procedure_name", labels["procedure"]),
            ("current_price", labels["price"]),
            ("material_cost", labels["material_cost"]),
            ("material_margin", labels["margin"]),
            ("margin_percent", labels["margin_percent"]),
            ("coverage_percent", labels["coverage"]),
            ("confidence", labels["confidence"]),
            ("status", labels["status"]),
        ],
        rows=rows,
        metadata={
            labels["definition"]: "estimated-material-margin-v2",
            labels["scope"]: "materials_only",
            labels["filter"]: search or "",
            labels["complete"]: completeness["complete"],
            labels["partial"]: completeness["partial"],
            labels["unavailable"]: completeness["unavailable"],
            labels["errors"]: completeness["errors"],
        },
    )
    return Response(
        content=csv_text.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=finance-material-margin.csv",
            "X-Content-Type-Options": "nosniff",
        },
    )


# Canonical operational-page exports live under the same /financials/reports
# namespace without recreating their financial calculations here.
from backend.routers.finance_exports import router as operational_exports_router

router.include_router(operational_exports_router)
