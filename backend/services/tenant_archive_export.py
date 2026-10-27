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
    tables = models.Base.metadata.tables
    for name, columns in ARCHIVE_COLUMNS.items():
        table = tables[name]
        query = select(*(table.c[column] for column in sorted(columns)))
        if 'tenant_id' in table.c:
            query = query.where(table.c.tenant_id == tenant_id)
        elif name == 'price_list_items':
            lists = tables['price_lists']
            query = query.join(lists, table.c.price_list_id == lists.c.id).where(lists.c.tenant_id == tenant_id)
        else:
            raise ValueError(f'Unsupported archive ownership: {name}')
        rows = (await db.execute(query)).mappings().all()
        result[name] = [{column: _serialize(value) for column, value in row.items()} for row in rows]
    users = tables['users']
    query = select(*(users.c[column] for column in sorted(STAFF_REFERENCE_COLUMNS))).where(users.c.tenant_id == tenant_id)
    result['staff_references'] = [
        {column: _serialize(value) for column, value in row.items()}
        for row in (await db.execute(query)).mappings().all()
    ]
    return {'data': result}
