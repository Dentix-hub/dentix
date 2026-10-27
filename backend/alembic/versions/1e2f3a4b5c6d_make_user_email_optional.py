"""Allow clinic users without an email address.

Revision ID: 1e2f3a4b5c6d
Revises: 0d1e2f3a4b5c
"""

from alembic import op
import sqlalchemy as sa

revision = "1e2f3a4b5c6d"
down_revision = "0d1e2f3a4b5c"
branch_labels = None
depends_on = None


def _set_nullable(nullable: bool) -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("users") as batch:
            batch.alter_column("email", existing_type=sa.String(), nullable=nullable)
    else:
        op.alter_column("users", "email", existing_type=sa.String(), nullable=nullable)


def upgrade() -> None:
    _set_nullable(True)


def downgrade() -> None:
    count = op.get_bind().execute(
        sa.text("SELECT count(*) FROM users WHERE email IS NULL")
    ).scalar_one()
    if count:
        raise RuntimeError(
            "Cannot restore users.email NOT NULL while NULL emails exist; "
            "assign valid unique email addresses before downgrading."
        )
    _set_nullable(False)
