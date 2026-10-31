"""Care Session Workflow Unification: explicit procedure associations, drafts, stable step identities, historical sessions, traceable amendments, and follow-up ownership.

Revision ID: b1c2d3e4f5a6
Revises: f3c4d5e6a7b8
"""
from alembic import op
import sqlalchemy as sa

revision = "b1c2d3e4f5a6"
down_revision = "f3c4d5e6a7b8"
branch_labels = None
depends_on = None

TENANT_TABLES = ("care_session_procedures", "care_session_drafts")


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    is_pg = bind.dialect.name == "postgresql"

    # 1. Update treatment_sessions (add next_session_date)
    if "treatment_sessions" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("treatment_sessions")}
        if "next_session_date" not in cols:
            op.add_column("treatment_sessions", sa.Column("next_session_date", sa.DateTime(), nullable=True))

    # 2. Update care_sessions
    if "care_sessions" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("care_sessions")}
        if "actual_visit_date" not in cols:
            op.add_column("care_sessions", sa.Column("actual_visit_date", sa.DateTime(timezone=True), nullable=True))
        if "recorded_by_user_id" not in cols:
            op.add_column("care_sessions", sa.Column("recorded_by_user_id", sa.Integer(), nullable=True))
        if "is_historical" not in cols:
            op.add_column("care_sessions", sa.Column("is_historical", sa.Boolean(), server_default=sa.false(), nullable=False))
        if "amends_session_id" not in cols:
            op.add_column("care_sessions", sa.Column("amends_session_id", sa.Integer(), nullable=True))
        if "amendment_reason" not in cols:
            op.add_column("care_sessions", sa.Column("amendment_reason", sa.Text(), nullable=True))

        idxs = {idx["name"] for idx in inspector.get_indexes("care_sessions")}
        if "ix_cs_tenant_actual_visit" not in idxs:
            op.create_index("ix_cs_tenant_actual_visit", "care_sessions", ["tenant_id", "actual_visit_date"])

    # 3. Update care_session_steps
    if "care_session_steps" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("care_session_steps")}
        if "logical_step_code" not in cols:
            op.add_column("care_session_steps", sa.Column("logical_step_code", sa.String(64), nullable=True))
        if "occurrence_number" not in cols:
            op.add_column("care_session_steps", sa.Column("occurrence_number", sa.Integer(), server_default="1", nullable=False))
        if "template_step_id" not in cols:
            op.add_column("care_session_steps", sa.Column("template_step_id", sa.String(64), nullable=True))
        if "is_repeat" not in cols:
            op.add_column("care_session_steps", sa.Column("is_repeat", sa.Boolean(), server_default=sa.false(), nullable=False))
        if "repeat_reason" not in cols:
            op.add_column("care_session_steps", sa.Column("repeat_reason", sa.Text(), nullable=True))

        idxs = {idx["name"] for idx in inspector.get_indexes("care_session_steps")}
        if "ix_css_tenant_wi_logical_step" not in idxs:
            op.create_index("ix_css_tenant_wi_logical_step", "care_session_steps", ["tenant_id", "work_item_id", "logical_step_code"])

    # 4. Update care_observations
    if "care_observations" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("care_observations")}
        if "is_superseded" not in cols:
            op.add_column("care_observations", sa.Column("is_superseded", sa.Boolean(), server_default=sa.false(), nullable=False))
        if "superseded_by_id" not in cols:
            op.add_column("care_observations", sa.Column("superseded_by_id", sa.Integer(), nullable=True))
        if "amendment_reason" not in cols:
            op.add_column("care_observations", sa.Column("amendment_reason", sa.Text(), nullable=True))
        if "reference_source_session_id" not in cols:
            op.add_column("care_observations", sa.Column("reference_source_session_id", sa.Integer(), nullable=True))
        if "reference_source_date" not in cols:
            op.add_column("care_observations", sa.Column("reference_source_date", sa.DateTime(timezone=True), nullable=True))

    # 5. Update next_visit_requests
    if "next_visit_requests" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("next_visit_requests")}
        if "associated_work_item_ids" not in cols:
            op.add_column("next_visit_requests", sa.Column("associated_work_item_ids", sa.JSON(), nullable=True))
        if "assigned_doctor_id" not in cols:
            op.add_column("next_visit_requests", sa.Column("assigned_doctor_id", sa.Integer(), nullable=True))
        if "stopped_at" not in cols:
            op.add_column("next_visit_requests", sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True))
        if "stopped_reason" not in cols:
            op.add_column("next_visit_requests", sa.Column("stopped_reason", sa.Text(), nullable=True))
        if "stopped_by_user_id" not in cols:
            op.add_column("next_visit_requests", sa.Column("stopped_by_user_id", sa.Integer(), nullable=True))
        if "postponed_to_date" not in cols:
            op.add_column("next_visit_requests", sa.Column("postponed_to_date", sa.DateTime(timezone=True), nullable=True))
        if "postponed_reason" not in cols:
            op.add_column("next_visit_requests", sa.Column("postponed_reason", sa.Text(), nullable=True))
        if "postponed_by_user_id" not in cols:
            op.add_column("next_visit_requests", sa.Column("postponed_by_user_id", sa.Integer(), nullable=True))
        if "handoff_at" not in cols:
            op.add_column("next_visit_requests", sa.Column("handoff_at", sa.DateTime(timezone=True), nullable=True))
        if "handoff_reason" not in cols:
            op.add_column("next_visit_requests", sa.Column("handoff_reason", sa.Text(), nullable=True))
        if "handoff_by_user_id" not in cols:
            op.add_column("next_visit_requests", sa.Column("handoff_by_user_id", sa.Integer(), nullable=True))
        if "handoff_to_user_id" not in cols:
            op.add_column("next_visit_requests", sa.Column("handoff_to_user_id", sa.Integer(), nullable=True))

    # 6. Create care_session_procedures table
    if "care_session_procedures" not in existing_tables:
        op.create_table(
            "care_session_procedures",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("care_session_id", sa.Integer(), sa.ForeignKey("care_sessions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("work_item_id", sa.Integer(), sa.ForeignKey("clinical_work_items.id", ondelete="CASCADE"), nullable=False),
            sa.Column("procedure_notes", sa.Text(), nullable=True),
            sa.Column("next_action", sa.Text(), nullable=True),
            sa.Column("next_action_reason_omitted", sa.Text(), nullable=True),
            sa.Column("template_snapshot", sa.JSON(), nullable=True),
            sa.Column("template_version", sa.Integer(), nullable=True),
            sa.Column("performing_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("care_session_id", "work_item_id", name="uq_csp_session_work_item"),
        )
        op.create_index("ix_care_session_procedures_id", "care_session_procedures", ["id"])
        op.create_index("ix_care_session_procedures_tenant_id", "care_session_procedures", ["tenant_id"])
        op.create_index("ix_csp_tenant_session", "care_session_procedures", ["tenant_id", "care_session_id"])
        op.create_index("ix_csp_tenant_work_item", "care_session_procedures", ["tenant_id", "work_item_id"])

    # 7. Create care_session_drafts table
    if "care_session_drafts" not in existing_tables:
        op.create_table(
            "care_session_drafts",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False),
            sa.Column("care_session_id", sa.Integer(), sa.ForeignKey("care_sessions.id", ondelete="CASCADE"), nullable=True),
            sa.Column("author_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("draft_payload", sa.JSON(), nullable=False),
            sa.Column("version_id", sa.Integer(), server_default="1", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("tenant_id", "patient_id", "author_user_id", "care_session_id", name="uq_csd_tenant_patient_author_session"),
        )
        op.create_index("ix_care_session_drafts_id", "care_session_drafts", ["id"])
        op.create_index("ix_care_session_drafts_tenant_id", "care_session_drafts", ["tenant_id"])
        op.create_index("ix_csd_tenant_patient_author", "care_session_drafts", ["tenant_id", "patient_id", "author_user_id"])
        op.create_index("ix_csd_tenant_session", "care_session_drafts", ["tenant_id", "care_session_id"])

    # 8. RLS and PostgreSQL Triggers
    if is_pg:
        new_tables = ["care_session_procedures", "care_session_drafts"]
        tenant_expr = "tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer"
        for table in new_tables:
            op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
            op.execute(f'DROP POLICY IF EXISTS "{table}_tenant_policy" ON "{table}"')
            op.execute(
                f'''CREATE POLICY "{table}_tenant_policy" ON "{table}"
                    FOR ALL
                    USING ({tenant_expr})
                    WITH CHECK ({tenant_expr})'''
            )

        relationships = [
            ("care_session_procedures", "care_session_id", "care_sessions", False),
            ("care_session_procedures", "work_item_id", "clinical_work_items", False),
            ("care_session_drafts", "patient_id", "patients", False),
            ("care_session_drafts", "care_session_id", "care_sessions", True),
        ]
        for table, child_key, parent, allow_null in relationships:
            trigger = f"trg_{table}_{child_key}_parent_tenant"
            op.execute(f'DROP TRIGGER IF EXISTS "{trigger}" ON "{table}"')
            op.execute(
                f'''CREATE TRIGGER "{trigger}"
                    BEFORE INSERT OR UPDATE OF tenant_id, "{child_key}" ON "{table}"
                    FOR EACH ROW
                    EXECUTE FUNCTION dentix_assert_parent_tenant('{parent}', '{child_key}', '{str(allow_null).lower()}')'''
            )

        # Install restore write gates for new tables
        for table in new_tables:
            op.execute(f'DROP TRIGGER IF EXISTS clinic_write_gate ON "{table}"')
            op.execute(
                f'CREATE TRIGGER clinic_write_gate BEFORE INSERT OR UPDATE OR DELETE ON "{table}" '
                f'FOR EACH ROW EXECUTE FUNCTION dentix_clinic_write_gate()'
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    is_pg = bind.dialect.name == "postgresql"

    if is_pg:
        for table in ["care_session_procedures", "care_session_drafts"]:
            op.execute(f'DROP TRIGGER IF EXISTS clinic_write_gate ON "{table}"')

    if "care_session_drafts" in existing_tables:
        op.drop_table("care_session_drafts")
    if "care_session_procedures" in existing_tables:
        op.drop_table("care_session_procedures")
