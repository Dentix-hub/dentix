"""Align care-workflow indexes, strict RLS and parent guards across install paths.

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
"""
from alembic import op
import sqlalchemy as sa

revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None

INDEXES = (
    ("care_sessions", "ix_care_sessions_amends_session_id", ("amends_session_id",)),
    ("care_sessions", "ix_care_sessions_recorded_by_user_id", ("recorded_by_user_id",)),
    ("care_session_drafts", "ix_care_session_drafts_author_user_id", ("author_user_id",)),
    ("care_session_drafts", "ix_care_session_drafts_care_session_id", ("care_session_id",)),
    ("care_session_drafts", "ix_care_session_drafts_patient_id", ("patient_id",)),
    ("care_session_procedures", "ix_care_session_procedures_care_session_id", ("care_session_id",)),
    ("care_session_procedures", "ix_care_session_procedures_performing_user_id", ("performing_user_id",)),
    ("care_session_procedures", "ix_care_session_procedures_work_item_id", ("work_item_id",)),
    ("next_visit_requests", "ix_next_visit_requests_assigned_doctor_id", ("assigned_doctor_id",)),
    ("next_visit_requests", "ix_next_visit_requests_handoff_by_user_id", ("handoff_by_user_id",)),
    ("next_visit_requests", "ix_next_visit_requests_handoff_to_user_id", ("handoff_to_user_id",)),
    ("next_visit_requests", "ix_next_visit_requests_postponed_by_user_id", ("postponed_by_user_id",)),
    ("next_visit_requests", "ix_next_visit_requests_stopped_by_user_id", ("stopped_by_user_id",)),
    ("next_visit_requests", "ix_nvr_tenant_assigned_doc", ("tenant_id", "assigned_doctor_id")),
    ("care_observations", "ix_care_observations_reference_source_observation_id", ("reference_source_observation_id",)),
    ("care_observations", "ix_care_observations_reference_source_session_id", ("reference_source_session_id",)),
    ("care_observations", "ix_care_observations_superseded_by_id", ("superseded_by_id",)),
)

PARENT_GUARDS = (
    ("care_session_procedures", "care_session_id", "care_sessions", False),
    ("care_session_procedures", "work_item_id", "clinical_work_items", False),
    ("care_session_drafts", "patient_id", "patients", False),
    ("care_session_drafts", "care_session_id", "care_sessions", True),
)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {table: {index["name"] for index in inspector.get_indexes(table)}
                for table, _, _ in INDEXES}
    for table, name, columns in INDEXES:
        if name not in existing[table]:
            op.create_index(name, table, list(columns))
    if bind.dialect.name == "postgresql":
        tenant_expr = "tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer"
        for table in ("care_session_procedures", "care_session_drafts"):
            # Metadata bootstrap previously retained the RLS package's GUC
            # bypass policies. A permissive legacy policy would also override
            # a strict policy, so remove every old policy before installing it.
            policies = list(bind.execute(sa.text(
                "SELECT policyname FROM pg_policies WHERE schemaname = current_schema() AND tablename = :table"
            ), {"table": table}).scalars())
            for policy in policies:
                quoted_policy = bind.dialect.identifier_preparer.quote(policy)
                op.execute(f'DROP POLICY {quoted_policy} ON "{table}"')
            op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
            op.execute(
                f'CREATE POLICY "{table}_tenant_policy" ON "{table}" FOR ALL '
                f'USING ({tenant_expr}) WITH CHECK ({tenant_expr})'
            )
        # Repair b1 databases created through the former metadata bootstrap,
        # as well as preserving the upgrade path's existing guards.
        for table, key, parent, allow_null in PARENT_GUARDS:
            trigger = f"trg_{table}_{key}_parent_tenant"
            op.execute(f'DROP TRIGGER IF EXISTS "{trigger}" ON "{table}"')
            op.execute(
                f'CREATE TRIGGER "{trigger}" BEFORE INSERT OR UPDATE OF tenant_id, "{key}" ON "{table}" '
                f"FOR EACH ROW EXECUTE FUNCTION dentix_assert_parent_tenant('{parent}', '{key}', '{str(allow_null).lower()}')"
            )


def downgrade():
    inspector = sa.inspect(op.get_bind())
    existing = {table: {index["name"] for index in inspector.get_indexes(table)}
                for table, _, _ in INDEXES}
    for table, name, _ in reversed(INDEXES):
        if name in existing[table]:
            op.drop_index(name, table_name=table)
    # Parent guards belong to b1 and remain installed on downgrade to b1.
