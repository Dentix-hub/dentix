"""Resolve archived staff references to current clinic identities."""
from sqlalchemy import select

from backend import models
from backend.services.tenant_archive import ArchiveError


async def resolve_staff_mapping(db, tenant_id, staff_references):
    """Map every archived staff ID to one existing user of the same tenant.

    IDs are accepted only with matching usernames. Otherwise, a unique exact
    case-folded username must resolve; ambiguity or missing data fails closed.
    Credentials and permission fields are never changed by this operation.
    """
    users = (await db.execute(select(models.User).where(models.User.tenant_id == tenant_id))).scalars().all()
    by_id = {user.id: user for user in users}
    by_name = {}
    for user in users:
        if user.username:
            by_name.setdefault(user.username.casefold(), []).append(user)
    mapping = {}
    used = set()
    for reference in staff_references:
        old_id, username = reference.get('id'), reference.get('username')
        if not isinstance(old_id, int) or isinstance(old_id, bool) or not isinstance(username, str) or not username:
            raise ArchiveError('تعذر مطابقة أحد حسابات العاملين في النسخة الاحتياطية')
        candidates = by_name.get(username.casefold(), [])
        if len(candidates) != 1:
            raise ArchiveError('تعذر مطابقة أحد حسابات العاملين في النسخة الاحتياطية')
        selected = candidates[0]
        by_old_id = by_id.get(old_id)
        if by_old_id is not None and by_old_id.id != selected.id:
            raise ArchiveError('تعذر مطابقة أحد حسابات العاملين في النسخة الاحتياطية')
        if selected.id in used or old_id in mapping:
            raise ArchiveError('تحتوي النسخة الاحتياطية على حسابات عاملين مكررة')
        mapping[old_id] = selected.id
        used.add(selected.id)
    return mapping
