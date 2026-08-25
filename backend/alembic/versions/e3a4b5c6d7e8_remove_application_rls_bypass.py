"""remove application-controlled RLS bypass from live policies

Revision ID: e3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-08-25

Cross-tenant maintenance now uses a physically separate PostgreSQL login with
the native BYPASSRLS role attribute.  The ordinary NOBYPASSRLS application
login cannot promote itself by setting a custom session variable.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "e3a4b5c6d7e8"
down_revision: Union[str, Sequence[str], None] = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute(
        r"""
        DO $$
        DECLARE
            policy_row record;
            tenant_expression text;
            alter_clauses text;
        BEGIN
            FOR policy_row IN
                SELECT tablename, policyname, qual, with_check
                  FROM pg_policies
                 WHERE schemaname = current_schema()
                   AND (
                       COALESCE(qual, '') LIKE '%rls.bypass_rls%'
                       OR COALESCE(with_check, '') LIKE '%rls.bypass_rls%'
                   )
            LOOP
                IF policy_row.tablename = 'notifications' THEN
                    tenant_expression :=
                        '((tenant_id = NULLIF(current_setting(''rls.tenant_id'', true), '''')::integer) '
                        'OR (is_global = true) OR (tenant_id IS NULL))';
                ELSE
                    tenant_expression :=
                        '(tenant_id = NULLIF(current_setting(''rls.tenant_id'', true), '''')::integer)';
                END IF;

                alter_clauses := '';
                IF policy_row.qual IS NOT NULL THEN
                    alter_clauses := alter_clauses || ' USING (' || tenant_expression || ')';
                END IF;
                IF policy_row.with_check IS NOT NULL THEN
                    alter_clauses := alter_clauses || ' WITH CHECK (' || tenant_expression || ')';
                END IF;

                EXECUTE format(
                    'ALTER POLICY %I ON %I%s',
                    policy_row.policyname,
                    policy_row.tablename,
                    alter_clauses
                );
            END LOOP;
        END
        $$
        """
    )


def downgrade() -> None:
    raise RuntimeError(
        "Refusing to restore an application-controlled cross-tenant RLS bypass"
    )
