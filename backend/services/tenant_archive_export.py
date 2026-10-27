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


async def export_clinic_archive_data(db, tenant_id):
    """Export only explicit business columns, preserving exact decimal values.

    Staff references never contain login credentials, roles, permissions or
    sessions. The importer must map every reference to a live tenant user.
    """
    result = {}
    classes = {mapper.local_table.name: mapper.class_ for mapper in models.Base.registry.mappers}
    for name, columns in ARCHIVE_COLUMNS.items():
        model = classes[name]
        query = select(model)
        if hasattr(model, 'tenant_id'):
            query = query.where(model.tenant_id == tenant_id)
        elif name == 'price_list_items':
            query = query.join(models.PriceList, model.price_list_id == models.PriceList.id).where(models.PriceList.tenant_id == tenant_id)
        else:
            raise ValueError(f'Unsupported archive ownership: {name}')
        rows = (await db.execute(query)).scalars().all()
        result[name] = [{column: _serialize(getattr(row, column)) for column in columns} for row in rows]
    query = select(models.User).where(models.User.tenant_id == tenant_id)
    result['staff_references'] = [
        {column: _serialize(getattr(user, column)) for column in STAFF_REFERENCE_COLUMNS}
        for user in (await db.execute(query)).scalars().all()
    ]
    return {'data': result}
