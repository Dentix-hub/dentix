"""Server-side CSV exports for canonical Finance operational pages.

These endpoints replace the retired duplicate report tabs.  Each export reads
from the same service/CRUD contract as its owning page and applies the active
filters on the server.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend import crud, schemas
from backend.core.permissions import Permission, require_permission
from backend.core.tenant_context import require_tenant_id
from backend.database import get_async_db
from backend.services.accounting_service import AccountingService
from backend.services.finance_report_service import FinanceReportService, build_csv_document
from backend.services.finance_summary_service import FinanceSummaryService
from backend.services.tenant_time_service import get_tenant_timezone

router = APIRouter(prefix="/accounting/reports", tags=["Finance Reports"])


def _csv_response(content: str, filename: str) -> Response:
    return Response(
        content=content.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Content-Type-Options": "nosniff",
        },
    )


def _period_metadata(locale: str, *, start: str, end: str, timezone: str) -> dict:
    if locale == "ar":
        return {
            "الفترة": f"{start} → {end}",
            "المنطقة الزمنية": timezone,
        }
    return {
        "Period": f"{start} → {end}",
        "Timezone": timezone,
    }


@router.get("/summary/export.csv")
async def export_summary_csv(
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    locale: str = Query("en", pattern="^(ar|en)$"),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.REPORT_EXPORT)),
):
    tenant_id = require_tenant_id(current_user)
    service = FinanceSummaryService(db, tenant_id)
    try:
        data = await service.get_summary(start_date=start_date, end_date=end_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    report_service = FinanceReportService(db, tenant_id)
    rows = []
    labels_by_metric = {
        "en": {
            "net_invoiced": "Net invoiced",
            "collected": "Collected",
            "manual_expenses": "Manual expenses",
            "lab_costs": "Lab costs",
            "doctor_dues": "Doctor dues",
            "staff_dues": "Staff dues",
            "total_deductions": "Total deductions",
            "net_operational_result": "Net operational result",
        },
        "ar": {
            "net_invoiced": "صافي المحتسب",
            "collected": "المحصل",
            "manual_expenses": "المصروفات التشغيلية",
            "lab_costs": "تكاليف المعامل",
            "doctor_dues": "مستحقات الأطباء",
            "staff_dues": "مستحقات الموظفين",
            "total_deductions": "إجمالي الاستقطاعات",
            "net_operational_result": "صافي النتيجة التشغيلية",
        },
    }[locale]
    for metric, path in report_service.METRIC_PATHS.items():
        rows.append(
            {
                "metric": labels_by_metric.get(metric, metric),
                "value": report_service._value(data, path),
            }
        )

    period = data.get("period", {})
    metadata = _period_metadata(
        locale,
        start=period.get("start", start_date),
        end=period.get("end", end_date),
        timezone=period.get("timezone", ""),
    )
    metadata[
        "إصدار التعريف" if locale == "ar" else "Definition version"
    ] = data.get("definition_version", "")
    metadata["العملة" if locale == "ar" else "Currency"] = data.get("currency", "EGP")

    columns = (
        [("metric", "المؤشر"), ("value", "القيمة")]
        if locale == "ar"
        else [("metric", "Metric"), ("value", "Value")]
    )
    return _csv_response(
        build_csv_document(columns=columns, rows=rows, metadata=metadata),
        "finance-summary.csv",
    )


@router.get("/patient-accounts/export.csv")
async def export_patient_accounts_csv(
    search: Optional[str] = Query(None, max_length=200),
    patient_id: Optional[int] = Query(None, ge=1),
    outstanding_only: bool = Query(False),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    locale: str = Query("en", pattern="^(ar|en)$"),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.REPORT_EXPORT)),
):
    if bool(start_date) != bool(end_date):
        raise HTTPException(status_code=400, detail="Both start_date and end_date are required together")

    tenant_id = require_tenant_id(current_user)
    service = AccountingService(db, tenant_id)
    start = end = None
    if start_date and end_date:
        try:
            start, end = service.parse_date_range(start_date, end_date)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid date range") from exc

    rows = []
    skip = 0
    batch_size = 200
    total = None
    summary = {}
    while total is None or skip < total:
        page = await service.get_patients_report(
            patient_id=patient_id,
            search=search,
            outstanding_only=outstanding_only,
            start=start,
            end=end,
            skip=skip,
            limit=batch_size,
        )
        total = int(page.get("total", 0))
        if not summary:
            summary = page.get("summary", {}) or {}
        page_rows = page.get("patients", []) or []
        rows.extend(page_rows)
        if not page_rows:
            break
        skip += len(page_rows)

    timezone = await get_tenant_timezone(db, tenant_id)
    metadata = {
        ("المنطقة الزمنية" if locale == "ar" else "Timezone"): timezone,
        ("إجمالي النتائج" if locale == "ar" else "Total rows"): total or 0,
        ("فلتر البحث" if locale == "ar" else "Search filter"): search or "",
        ("مدينون فقط" if locale == "ar" else "Outstanding only"): outstanding_only,
        ("إجمالي المديونية الحالية" if locale == "ar" else "Current total receivables"): summary.get("total_outstanding", ""),
    }
    if start_date and end_date:
        metadata.update(
            _period_metadata(
                locale,
                start=start_date,
                end=end_date,
                timezone=timezone,
            )
        )

    columns = {
        "en": [
            ("file_number", "File number"),
            ("patient_name", "Patient"),
            ("patient_phone", "Phone"),
            ("total_invoiced", "Invoiced in period"),
            ("total_paid", "Paid in period"),
            ("outstanding_balance", "Period balance"),
            ("all_time_outstanding", "Current outstanding"),
        ],
        "ar": [
            ("file_number", "رقم الملف"),
            ("patient_name", "المريض"),
            ("patient_phone", "الهاتف"),
            ("total_invoiced", "المحتسب في الفترة"),
            ("total_paid", "المدفوع في الفترة"),
            ("outstanding_balance", "رصيد الفترة"),
            ("all_time_outstanding", "المديونية الحالية"),
        ],
    }[locale]
    return _csv_response(
        build_csv_document(columns=columns, rows=rows, metadata=metadata),
        "finance-patient-accounts.csv",
    )


@router.get("/expenses/export.csv")
async def export_expenses_csv(
    search: Optional[str] = Query(None, max_length=200),
    category: Optional[str] = Query(None, max_length=100),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    locale: str = Query("en", pattern="^(ar|en)$"),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.REPORT_EXPORT)),
):
    if bool(start_date) != bool(end_date):
        raise HTTPException(status_code=400, detail="Both start_date and end_date are required together")

    tenant_id = require_tenant_id(current_user)
    total = await crud.count_expenses(
        db,
        tenant_id,
        search=search,
        category=category,
        start_date=start_date,
        end_date=end_date,
    )
    rows = []
    skip = 0
    batch_size = 200
    while skip < total:
        page_rows = await crud.get_expenses(
            db,
            tenant_id,
            skip=skip,
            limit=batch_size,
            search=search,
            category=category,
            start_date=start_date,
            end_date=end_date,
        )
        rows.extend(
            {
                "date": expense.date,
                "item_name": expense.item_name,
                "category": expense.category,
                "cost": expense.cost,
                "notes": expense.notes,
                "source": "manual_expense",
            }
            for expense in page_rows
        )
        if not page_rows:
            break
        skip += len(page_rows)

    timezone = await get_tenant_timezone(db, tenant_id)
    metadata = {
        ("المنطقة الزمنية" if locale == "ar" else "Timezone"): timezone,
        ("إجمالي النتائج" if locale == "ar" else "Total rows"): total,
        ("فلتر البحث" if locale == "ar" else "Search filter"): search or "",
        ("التصنيف" if locale == "ar" else "Category"): category or "",
        ("المصدر" if locale == "ar" else "Source"): "manual_expense",
    }
    if start_date and end_date:
        metadata.update(_period_metadata(locale, start=start_date, end=end_date, timezone=timezone))

    columns = {
        "en": [
            ("date", "Date"),
            ("item_name", "Expense"),
            ("category", "Category"),
            ("cost", "Amount"),
            ("notes", "Notes"),
            ("source", "Source"),
        ],
        "ar": [
            ("date", "التاريخ"),
            ("item_name", "بيان المصروف"),
            ("category", "التصنيف"),
            ("cost", "المبلغ"),
            ("notes", "ملاحظات"),
            ("source", "المصدر"),
        ],
    }[locale]
    return _csv_response(
        build_csv_document(columns=columns, rows=rows, metadata=metadata),
        "finance-expenses.csv",
    )


@router.get("/providers/export.csv")
async def export_providers_csv(
    start_date: str = Query(...),
    end_date: str = Query(...),
    search: Optional[str] = Query(None, max_length=200),
    locale: str = Query("en", pattern="^(ar|en)$"),
    db: AsyncSession = Depends(get_async_db),
    current_user: schemas.User = Depends(require_permission(Permission.REPORT_EXPORT)),
):
    tenant_id = require_tenant_id(current_user)
    service = AccountingService(db, tenant_id)
    try:
        start, end = service.parse_date_range(start_date, end_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date range") from exc
    rows = await service.get_doctor_revenue_analytics(start, end)
    if search:
        needle = search.strip().casefold()
        rows = [row for row in rows if needle in str(row.get("doctor_name", "")).casefold()]

    timezone = await get_tenant_timezone(db, tenant_id)
    metadata = _period_metadata(locale, start=start_date, end=end_date, timezone=timezone)
    metadata[("فلتر البحث" if locale == "ar" else "Search filter")] = search or ""
    metadata[("إجمالي النتائج" if locale == "ar" else "Total rows")] = len(rows)

    columns = {
        "en": [
            ("doctor_name", "Provider"),
            ("treatments", "Treatments"),
            ("revenue", "Net production"),
            ("collected", "Collected attribution"),
            ("lab_cost", "Lab cost"),
            ("commission_percent", "Commission %"),
            ("commission_amount", "Commission amount"),
            ("fixed_salary_period", "Fixed salary in period"),
            ("total_due", "Total due"),
        ],
        "ar": [
            ("doctor_name", "الطبيب"),
            ("treatments", "الإجراءات"),
            ("revenue", "صافي الإنتاج"),
            ("collected", "التحصيل المنسوب"),
            ("lab_cost", "تكلفة المعمل"),
            ("commission_percent", "نسبة العمولة %"),
            ("commission_amount", "قيمة العمولة"),
            ("fixed_salary_period", "الراتب الثابت للفترة"),
            ("total_due", "إجمالي المستحق"),
        ],
    }[locale]
    return _csv_response(
        build_csv_document(columns=columns, rows=rows, metadata=metadata),
        "finance-providers.csv",
    )
