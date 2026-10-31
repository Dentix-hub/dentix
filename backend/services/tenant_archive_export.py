"""Export clinic business rows for the authenticated archive format."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select

from backend import models
from backend.services.tenant_archive_registry import ARCHIVE_COLUMNS, STAFF_REFERENCE_COLUMNS


def _serialize(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


async def export_clinic_archive_data(db, tenant_id, *, validate_restore=True):
    """Export only explicit business columns, preserving exact decimal values.

    Staff references never contain login credentials, roles, permissions or
    sessions. The importer must map every reference to a live tenant user.
    When validate_restore is True, executes shared restore preflight checks so
    the export fails early if business data is incompatible with recovery.
    """
    from backend.services.drive_image_safety import ensure_no_active_image_operations
    await ensure_no_active_image_operations(db, tenant_id)
    result = {}
    classes = {mapper.local_table.name: mapper.class_ for mapper in models.Base.registry.mappers}
    for name, columns in ARCHIVE_COLUMNS.items():
        model = classes[name]
        table = model.__table__
        query = select(*[table.c[column] for column in columns])
        if "tenant_id" in table.c:
            query = query.where(table.c.tenant_id == tenant_id)
        elif name == "price_list_items":
            price_lists_table = models.PriceList.__table__
            query = query.join(
                price_lists_table,
                table.c.price_list_id == price_lists_table.c.id,
            ).where(price_lists_table.c.tenant_id == tenant_id)
        else:
            raise ValueError(f"Unsupported archive ownership: {name}")
        rows = (await db.execute(query)).mappings().all()
        result[name] = [{column: _serialize(row[column]) for column in columns} for row in rows]
    user_table = models.User.__table__
    user_query = select(*[user_table.c[col] for col in STAFF_REFERENCE_COLUMNS]).where(
        user_table.c.tenant_id == tenant_id
    )
    user_rows = (await db.execute(user_query)).mappings().all()
    result["staff_references"] = [
        {column: _serialize(row[column]) for column in STAFF_REFERENCE_COLUMNS}
        for row in user_rows
    ]
    payload = {'data': result}
    from backend.services.tenant_archive_history import disclose_unresolved_treatment_history
    disclose_unresolved_treatment_history(result)
    if validate_restore:
        from backend.services.tenant_archive_registry import validate_archive_compatibility
        await validate_archive_compatibility(db, payload, tenant_id=tenant_id)
    return payload
