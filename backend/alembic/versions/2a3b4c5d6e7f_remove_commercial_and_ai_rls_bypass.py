"""remove application-controlled RLS bypass from commercial and ai policies

Revision ID: 2a3b4c5d6e7f
Revises: 1f2e3d4c5b6a
Create Date: 2026-11-04

Enforce strict PostgreSQL RLS invariants on commercial_tenant_overrides,
ai_quota_windows, and ai_reservations by removing application-controlled
GUC bypass ('rls.bypass_rls'). System operations bypass RLS via native
PostgreSQL BYPASSRLS role privilege rather than SQL policy bypass.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "2a3b4c5d6e7f"
down_revision: Union[str, Sequence[str], None] = "1f2e3d4c5b6a"
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
    pass
