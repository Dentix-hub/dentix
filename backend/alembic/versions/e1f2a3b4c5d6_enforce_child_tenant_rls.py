"""enforce tenant ownership and RLS for clinical/inventory child rows

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-08-25

The five child tables predate first-class tenant ownership.  This migration is
deliberately fail-closed: it refuses to continue when a child is orphaned, its
parent has no tenant, or an existing child tenant conflicts with the parent.
Only then does it backfill, make tenant_id mandatory, and install PostgreSQL
FORCE-RLS plus write-time parent/child consistency triggers.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CHILDREN = (
    ("tooth_status", "patient_id", "patients"),
    ("prescriptions", "patient_id", "patients"),
    ("attachments", "patient_id", "patients"),
    ("material_sessions", "stock_item_id", "stock_items"),
    ("stock_movements", "stock_item_id", "stock_items"),
)


def _quoted(name: str) -> str:
    return f'"{name}"'


def _ensure_tenant_column(table: str) -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns(table)}
    if "tenant_id" not in columns:
        op.add_column(table, sa.Column("tenant_id", sa.Integer(), nullable=True))


def _assert_and_backfill(table: str, child_key: str, parent: str) -> None:
    bind = op.get_bind()
    anomaly_count = bind.execute(
        sa.text(
            f"""
            SELECT COUNT(*)
              FROM {_quoted(table)} AS child
              LEFT JOIN {_quoted(parent)} AS parent
                ON parent.id = child.{_quoted(child_key)}
             WHERE parent.id IS NULL
                OR parent.tenant_id IS NULL
                OR (child.tenant_id IS NOT NULL
                    AND child.tenant_id <> parent.tenant_id)
            """
        )
    ).scalar_one()
    if anomaly_count:
        raise RuntimeError(
            f"Cannot assign {table}.tenant_id safely: {anomaly_count} "
            "orphaned, unowned, or cross-tenant row(s)"
        )

    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text(
                f"""
                UPDATE {_quoted(table)} AS child
                   SET tenant_id = parent.tenant_id
                  FROM {_quoted(parent)} AS parent
                 WHERE parent.id = child.{_quoted(child_key)}
                   AND child.tenant_id IS NULL
                """
            )
        )
    else:
        bind.execute(
            sa.text(
                f"""
                UPDATE {_quoted(table)}
                   SET tenant_id = (
                       SELECT parent.tenant_id
                         FROM {_quoted(parent)} AS parent
                        WHERE parent.id = {_quoted(table)}.{_quoted(child_key)}
                   )
                 WHERE tenant_id IS NULL
                """
            )
        )

    remaining = bind.execute(
        sa.text(f"SELECT COUNT(*) FROM {_quoted(table)} WHERE tenant_id IS NULL")
    ).scalar_one()
    if remaining:
        raise RuntimeError(f"Backfill left {remaining} unowned row(s) in {table}")


def _ensure_contract(table: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    index_name = f"ix_{table}_tenant_id"
    if index_name not in {index["name"] for index in inspector.get_indexes(table)}:
        op.create_index(index_name, table, ["tenant_id"], unique=False)

    tenant_fk_exists = any(
        fk.get("referred_table") == "tenants"
        and fk.get("constrained_columns") == ["tenant_id"]
        for fk in inspector.get_foreign_keys(table)
    )
    if bind.dialect.name == "postgresql":
        if not tenant_fk_exists:
            op.create_foreign_key(
                f"fk_{table}_tenant_id_tenants",
                table,
                "tenants",
                ["tenant_id"],
                ["id"],
                ondelete="RESTRICT",
            )
        op.alter_column(table, "tenant_id", existing_type=sa.Integer(), nullable=False)
    else:
        with op.batch_alter_table(table) as batch_op:
            if not tenant_fk_exists:
                batch_op.create_foreign_key(
                    f"fk_{table}_tenant_id_tenants",
                    "tenants",
                    ["tenant_id"],
                    ["id"],
                    ondelete="RESTRICT",
                )
            batch_op.alter_column("tenant_id", existing_type=sa.Integer(), nullable=False)


def _install_postgresql_guards() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        """
        CREATE OR REPLACE FUNCTION dentix_assert_parent_tenant()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            child_parent_id integer;
            parent_tenant_id integer;
            allow_null boolean := COALESCE(TG_ARGV[2], 'false')::boolean;
        BEGIN
            child_parent_id := NULLIF(to_jsonb(NEW) ->> TG_ARGV[1], '')::integer;
            IF child_parent_id IS NULL AND allow_null THEN
                RETURN NEW;
            END IF;
            IF child_parent_id IS NULL THEN
                RAISE EXCEPTION 'Missing required parent on %', TG_TABLE_NAME;
            END IF;
            EXECUTE format('SELECT tenant_id FROM %I WHERE id = $1', TG_ARGV[0])
               INTO parent_tenant_id USING child_parent_id;
            IF parent_tenant_id IS NULL OR NEW.tenant_id IS DISTINCT FROM parent_tenant_id THEN
                RAISE EXCEPTION 'Tenant mismatch on %', TG_TABLE_NAME;
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )

    tenant_expr = "tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer"
    for table, child_key, parent in CHILDREN:
        trigger = f"trg_{table}_parent_tenant"
        op.execute(f'DROP TRIGGER IF EXISTS "{trigger}" ON "{table}"')
        op.execute(
            f'''CREATE TRIGGER "{trigger}"
                BEFORE INSERT OR UPDATE OF tenant_id, "{child_key}" ON "{table}"
                FOR EACH ROW EXECUTE FUNCTION dentix_assert_parent_tenant(
                    '{parent}', '{child_key}', 'false'
                )'''
        )
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(f'DROP POLICY IF EXISTS "{table}_tenant_policy" ON "{table}"')
        op.execute(
            f'''CREATE POLICY "{table}_tenant_policy" ON "{table}"
                FOR ALL
                USING ({tenant_expr})
                WITH CHECK ({tenant_expr})'''
        )

    op.execute(
        'DROP TRIGGER IF EXISTS "trg_material_sessions_patient_tenant" '
        'ON "material_sessions"'
    )
    op.execute(
        '''CREATE TRIGGER "trg_material_sessions_patient_tenant"
           BEFORE INSERT OR UPDATE OF tenant_id, patient_id ON "material_sessions"
           FOR EACH ROW EXECUTE FUNCTION dentix_assert_parent_tenant(
               'patients', 'patient_id', 'true'
           )'''
    )


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    missing = sorted({table for table, _, _ in CHILDREN} - tables)
    if missing:
        raise RuntimeError(f"Required tenant child tables are missing: {missing}")

    for table, child_key, parent in CHILDREN:
        _ensure_tenant_column(table)
        _assert_and_backfill(table, child_key, parent)
        _ensure_contract(table)
    _install_postgresql_guards()


def downgrade() -> None:
    raise RuntimeError(
        "e1f2a3b4c5d6 is intentionally irreversible: removing tenant ownership or "
        "RLS would reintroduce cross-tenant exposure. Restore a verified pre-upgrade "
        "backup instead."
    )
