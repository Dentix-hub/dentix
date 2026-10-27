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
    op.add_column("treatments", sa.Column("request_key", sa.String(128), nullable=True))
    op.add_column("treatments", sa.Column("request_fingerprint", sa.String(64), nullable=True))
    op.create_index("uq_treatment_tenant_request_key", "treatments", ["tenant_id", "request_key"], unique=True)


def downgrade():
    op.drop_index("uq_treatment_tenant_request_key", table_name="treatments")
    op.drop_column("treatments", "request_fingerprint")
    op.drop_column("treatments", "request_key")
