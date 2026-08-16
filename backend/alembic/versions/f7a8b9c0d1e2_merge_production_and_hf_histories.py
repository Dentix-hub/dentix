"""merge production and HF staging migration histories

Revision ID: f7a8b9c0d1e2
Revises: a4b5c6d7e8f9, e4f5a6b7c8d9
Create Date: 2026-08-17 01:08:00.000000

Production had already advanced through the subscription checkout and patient
file-number migrations, while HF staging advanced through the global-procedure
migration from the same 0c0c38745bc3 base. This merge revision preserves both
valid histories and gives Alembic a single head without re-stamping or
rewriting deployed schema state.
"""

from typing import Sequence, Union


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = (
    "a4b5c6d7e8f9",
    "e4f5a6b7c8d9",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
