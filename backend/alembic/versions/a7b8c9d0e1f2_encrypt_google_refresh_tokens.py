"""Encrypt persisted Google OAuth refresh tokens.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
"""

from collections.abc import Sequence
import os

from alembic import op
import sqlalchemy as sa
from cryptography.fernet import Fernet, InvalidToken


revision: str = "a7b8c9d0e1f2"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SETTING_KEY = "google_refresh_token_super_admin"


def _token_rows(bind):
    tenant_rows = bind.execute(
        sa.text(
            "SELECT id, google_refresh_token FROM tenants "
            "WHERE google_refresh_token IS NOT NULL AND google_refresh_token <> ''"
        )
    ).fetchall()
    setting_rows = bind.execute(
        sa.text(
            "SELECT key, value FROM system_settings "
            "WHERE key = :key AND value IS NOT NULL AND value <> ''"
        ),
        {"key": _SETTING_KEY},
    ).fetchall()
    return tenant_rows, setting_rows


def _configured_fernet(bind) -> tuple[Fernet | None, tuple[list, list]]:
    rows = _token_rows(bind)
    if not rows[0] and not rows[1]:
        return None, rows

    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "ENCRYPTION_KEY is required to migrate existing Google refresh tokens"
        )
    try:
        return Fernet(key.encode()), rows
    except Exception as exc:
        raise RuntimeError("ENCRYPTION_KEY is not a valid Fernet key") from exc


def _encrypt_if_needed(fernet: Fernet, value: str) -> str:
    try:
        fernet.decrypt(value.encode())
        return value
    except InvalidToken:
        return fernet.encrypt(value.encode()).decode()


def upgrade() -> None:
    bind = op.get_bind()
    fernet, (tenant_rows, setting_rows) = _configured_fernet(bind)
    if fernet:
        for tenant_id, value in tenant_rows:
            bind.execute(
                sa.text(
                    "UPDATE tenants SET google_refresh_token = :value WHERE id = :id"
                ),
                {"value": _encrypt_if_needed(fernet, value), "id": tenant_id},
            )
        for key, value in setting_rows:
            bind.execute(
                sa.text("UPDATE system_settings SET value = :value WHERE key = :key"),
                {"value": _encrypt_if_needed(fernet, value), "key": key},
            )

    with op.batch_alter_table("tenants") as batch_op:
        batch_op.alter_column(
            "google_refresh_token",
            existing_type=sa.String(),
            type_=sa.String(length=2048),
            existing_nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    fernet, (tenant_rows, setting_rows) = _configured_fernet(bind)
    if fernet:
        for tenant_id, value in tenant_rows:
            try:
                plaintext = fernet.decrypt(value.encode()).decode()
            except InvalidToken:
                plaintext = value
            bind.execute(
                sa.text(
                    "UPDATE tenants SET google_refresh_token = :value WHERE id = :id"
                ),
                {"value": plaintext, "id": tenant_id},
            )
        for key, value in setting_rows:
            try:
                plaintext = fernet.decrypt(value.encode()).decode()
            except InvalidToken:
                plaintext = value
            bind.execute(
                sa.text("UPDATE system_settings SET value = :value WHERE key = :key"),
                {"value": plaintext, "key": key},
            )

    with op.batch_alter_table("tenants") as batch_op:
        batch_op.alter_column(
            "google_refresh_token",
            existing_type=sa.String(length=2048),
            type_=sa.String(),
            existing_nullable=True,
        )
