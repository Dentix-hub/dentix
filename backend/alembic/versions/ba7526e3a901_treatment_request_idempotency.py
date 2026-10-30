"""Store tenant-qualified treatment retry identities.

Revision ID: ba7526e3a901
Revises: 9ab047d5613e
"""
from alembic import op
import sqlalchemy as sa

revision = "ba7526e3a901"
down_revision = "9ab047d5613e"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "treatments" not in existing_tables:
        return

    cols = {c["name"] for c in inspector.get_columns("treatments")}
    if "request_key" not in cols:
        op.add_column("treatments", sa.Column("request_key", sa.String(128), nullable=True))
    if "request_fingerprint" not in cols:
        op.add_column("treatments", sa.Column("request_fingerprint", sa.String(64), nullable=True))

    indexes = {idx["name"] for idx in inspector.get_indexes("treatments")}
    if "uq_treatment_tenant_request_key" not in indexes:
        op.create_index("uq_treatment_tenant_request_key", "treatments", ["tenant_id", "request_key"], unique=True)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "treatments" not in existing_tables:
        return

    indexes = {idx["name"] for idx in inspector.get_indexes("treatments")}
    if "uq_treatment_tenant_request_key" in indexes:
        op.drop_index("uq_treatment_tenant_request_key", table_name="treatments")

    cols = {c["name"] for c in inspector.get_columns("treatments")}
    if "request_fingerprint" in cols:
        op.drop_column("treatments", "request_fingerprint")
    if "request_key" in cols:
        op.drop_column("treatments", "request_key")
