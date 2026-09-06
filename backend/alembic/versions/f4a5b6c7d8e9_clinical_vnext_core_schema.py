"""clinical vnext core schema

Revision ID: f4a5b6c7d8e9
Revises: e3a4b5c6d7e8
Create Date: 2026-09-06

Adds normalized additive clinical core tables:
- clinical_work_items
- clinical_work_item_targets
- clinical_treatment_plans
- clinical_treatment_plan_phases
- clinical_treatment_plan_items
- care_sessions
- care_session_steps
- clinical_events
- clinical_event_targets
- care_observations
- workflow_templates
- next_visit_requests
- clinical_attachment_links

Enforces tenant ownership, PostgreSQL ENABLE/FORCE RLS, fail-closed tenant
policies, parent-tenant FK triggers, and portable FDI/shape validation.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "e3a4b5c6d7e8"
branch_labels = None
depends_on = None

FDI_TOOTH_KEYS = (
    "11", "12", "13", "14", "15", "16", "17", "18",
    "21", "22", "23", "24", "25", "26", "27", "28",
    "31", "32", "33", "34", "35", "36", "37", "38",
    "41", "42", "43", "44", "45", "46", "47", "48",
    "51", "52", "53", "54", "55",
    "61", "62", "63", "64", "65",
    "71", "72", "73", "74", "75",
    "81", "82", "83", "84", "85",
)
FDI_CLAUSE = ", ".join(f"'{k}'" for k in FDI_TOOTH_KEYS)
SURFACE_CLAUSE = "'M', 'D', 'O', 'I', 'B', 'L', 'P'"
ROOT_CLAUSE = "'single', 'buccal', 'palatal', 'mesiobuccal', 'distobuccal', 'mesial', 'distal'"
TARGET_KIND_CLAUSE = "'tooth', 'surface', 'root', 'canal'"
TARGET_SHAPE_CONSTRAINT = (
    "("
    "(target_kind = 'tooth' AND surface_code IS NULL AND root_id IS NULL AND canal_id IS NULL) OR "
    "(target_kind = 'surface' AND surface_code IS NOT NULL AND root_id IS NULL AND canal_id IS NULL) OR "
    "(target_kind = 'root' AND surface_code IS NULL AND root_id IS NOT NULL AND canal_id IS NULL) OR "
    "(target_kind = 'canal' AND surface_code IS NULL AND root_id IS NOT NULL)"
    ")"
)

NEW_TABLES = (
    "clinical_work_items",
    "clinical_work_item_targets",
    "clinical_treatment_plans",
    "clinical_treatment_plan_phases",
    "clinical_treatment_plan_items",
    "care_sessions",
    "care_session_steps",
    "clinical_events",
    "clinical_event_targets",
    "care_observations",
    "workflow_templates",
    "next_visit_requests",
    "clinical_attachment_links",
)

NEW_CHILD_TENANT_RELATIONSHIPS = (
    ("clinical_work_items", "patient_id", "patients", False),
    ("clinical_work_items", "created_by_user_id", "users", True),
    ("clinical_work_item_targets", "work_item_id", "clinical_work_items", False),
    ("clinical_treatment_plans", "patient_id", "patients", False),
    ("clinical_treatment_plans", "created_by_user_id", "users", True),
    ("clinical_treatment_plan_phases", "plan_id", "clinical_treatment_plans", False),
    ("clinical_treatment_plan_items", "phase_id", "clinical_treatment_plan_phases", False),
    ("clinical_treatment_plan_items", "work_item_id", "clinical_work_items", False),
    ("care_sessions", "patient_id", "patients", False),
    ("care_sessions", "appointment_id", "appointments", True),
    ("care_sessions", "provider_user_id", "users", True),
    ("care_session_steps", "care_session_id", "care_sessions", False),
    ("care_session_steps", "work_item_id", "clinical_work_items", True),
    ("clinical_events", "patient_id", "patients", False),
    ("clinical_events", "work_item_id", "clinical_work_items", True),
    ("clinical_events", "care_session_id", "care_sessions", True),
    ("clinical_events", "actor_user_id", "users", True),
    ("clinical_event_targets", "event_id", "clinical_events", False),
    ("care_observations", "patient_id", "patients", False),
    ("care_observations", "care_session_id", "care_sessions", False),
    ("care_observations", "step_id", "care_session_steps", True),
    ("care_observations", "work_item_id", "clinical_work_items", True),
    ("care_observations", "recorded_by_user_id", "users", True),
    ("next_visit_requests", "patient_id", "patients", False),
    ("next_visit_requests", "care_session_id", "care_sessions", True),
    ("next_visit_requests", "work_item_id", "clinical_work_items", True),
    ("next_visit_requests", "requested_by_user_id", "users", True),
    ("clinical_attachment_links", "attachment_id", "attachments", False),
    ("clinical_attachment_links", "patient_id", "patients", False),
    ("clinical_attachment_links", "work_item_id", "clinical_work_items", True),
    ("clinical_attachment_links", "care_session_id", "care_sessions", True),
    ("clinical_attachment_links", "clinical_event_id", "clinical_events", True),
)

NEW_CHILD_PATIENT_RELATIONSHIPS = (
    ("clinical_attachment_links", "attachment_id", "attachments", False),
    ("clinical_attachment_links", "work_item_id", "clinical_work_items", True),
    ("clinical_attachment_links", "care_session_id", "care_sessions", True),
    ("clinical_attachment_links", "clinical_event_id", "clinical_events", True),
    ("care_sessions", "appointment_id", "appointments", True),
    ("care_observations", "care_session_id", "care_sessions", False),
    ("care_observations", "work_item_id", "clinical_work_items", True),
    ("clinical_events", "work_item_id", "clinical_work_items", True),
    ("clinical_events", "care_session_id", "care_sessions", True),
    ("next_visit_requests", "care_session_id", "care_sessions", True),
    ("next_visit_requests", "work_item_id", "clinical_work_items", True),
)

SPECIALIZED_G1_PATIENT_TRIGGERS = (
    ("clinical_treatment_plan_items", "trg_ctpi_phase_work_item_patient"),
    ("care_session_steps", "trg_css_session_work_item_patient"),
    ("care_observations", "trg_co_step_care_session_match"),
)


def _trigger_name(table: str, child_key: str) -> str:
    return f"trg_{table}_{child_key}_parent_tenant"


def _patient_trigger_name(table: str, child_key: str) -> str:
    return f"trg_{table}_{child_key}_parent_patient"


def upgrade() -> None:
    # 1. clinical_work_items
    op.create_table(
        "clinical_work_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="proposed", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("version_id", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("kind IN ('finding', 'procedure')", name="ck_clinical_work_items_kind"),
        sa.CheckConstraint("length(trim(code)) > 0", name="ck_clinical_work_items_code_not_empty"),
        sa.CheckConstraint("length(trim(status)) > 0", name="ck_clinical_work_items_status_not_empty"),
    )
    op.create_index("ix_clinical_work_items_id", "clinical_work_items", ["id"])
    op.create_index("ix_clinical_work_items_tenant_id", "clinical_work_items", ["tenant_id"])
    op.create_index("ix_clinical_work_items_patient_id", "clinical_work_items", ["patient_id"])
    op.create_index("ix_clinical_work_items_created_by_user_id", "clinical_work_items", ["created_by_user_id"])
    op.create_index("ix_clinical_work_items_tenant_patient", "clinical_work_items", ["tenant_id", "patient_id"])
    op.create_index("ix_clinical_work_items_tenant_kind", "clinical_work_items", ["tenant_id", "kind"])
    op.create_index("ix_clinical_work_items_tenant_status", "clinical_work_items", ["tenant_id", "status"])

    # 2. clinical_work_item_targets
    op.create_table(
        "clinical_work_item_targets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("work_item_id", sa.Integer(), sa.ForeignKey("clinical_work_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_kind", sa.String(length=16), nullable=False),
        sa.Column("tooth_key", sa.String(length=8), nullable=False),
        sa.Column("surface_code", sa.String(length=8), nullable=True),
        sa.Column("root_id", sa.String(length=32), nullable=True),
        sa.Column("canal_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(f"target_kind IN ({TARGET_KIND_CLAUSE})", name="ck_cwit_target_kind"),
        sa.CheckConstraint(f"tooth_key IN ({FDI_CLAUSE})", name="ck_cwit_tooth_key_fdi"),
        sa.CheckConstraint(f"surface_code IS NULL OR surface_code IN ({SURFACE_CLAUSE})", name="ck_cwit_surface_code"),
        sa.CheckConstraint(f"root_id IS NULL OR root_id IN ({ROOT_CLAUSE})", name="ck_cwit_root_id"),
        sa.CheckConstraint("canal_id IS NULL OR length(trim(canal_id)) > 0", name="ck_cwit_canal_id_not_empty"),
        sa.CheckConstraint(TARGET_SHAPE_CONSTRAINT, name="ck_cwit_shape"),
    )
    op.create_index("ix_clinical_work_item_targets_id", "clinical_work_item_targets", ["id"])
    op.create_index("ix_clinical_work_item_targets_tenant_id", "clinical_work_item_targets", ["tenant_id"])
    op.create_index("ix_clinical_work_item_targets_work_item_id", "clinical_work_item_targets", ["work_item_id"])
    op.create_index("ix_cwit_tenant_work_item", "clinical_work_item_targets", ["tenant_id", "work_item_id"])
    op.create_index(
        "uq_cwit_parent_target_exact",
        "clinical_work_item_targets",
        [
            "work_item_id",
            "target_kind",
            "tooth_key",
            sa.text("COALESCE(surface_code, '')"),
            sa.text("COALESCE(root_id, '')"),
            sa.text("COALESCE(canal_id, '')"),
        ],
        unique=True,
    )

    # 3. clinical_treatment_plans
    op.create_table(
        "clinical_treatment_plans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("version_id", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_ctp_title_not_empty"),
        sa.CheckConstraint("length(trim(status)) > 0", name="ck_ctp_status_not_empty"),
    )
    op.create_index("ix_clinical_treatment_plans_id", "clinical_treatment_plans", ["id"])
    op.create_index("ix_clinical_treatment_plans_tenant_id", "clinical_treatment_plans", ["tenant_id"])
    op.create_index("ix_clinical_treatment_plans_patient_id", "clinical_treatment_plans", ["patient_id"])
    op.create_index("ix_clinical_treatment_plans_created_by_user_id", "clinical_treatment_plans", ["created_by_user_id"])
    op.create_index("ix_ctp_tenant_patient", "clinical_treatment_plans", ["tenant_id", "patient_id"])
    op.create_index("ix_ctp_tenant_status", "clinical_treatment_plans", ["tenant_id", "status"])

    # 4. clinical_treatment_plan_phases
    op.create_table(
        "clinical_treatment_plan_phases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("clinical_treatment_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phase_order", sa.Integer(), server_default="1", nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("phase_order >= 0", name="ck_ctpp_phase_order_non_negative"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_ctpp_name_not_empty"),
        sa.CheckConstraint("length(trim(status)) > 0", name="ck_ctpp_status_not_empty"),
        sa.UniqueConstraint("plan_id", "phase_order", name="uq_ctpp_plan_phase_order"),
    )
    op.create_index("ix_clinical_treatment_plan_phases_id", "clinical_treatment_plan_phases", ["id"])
    op.create_index("ix_clinical_treatment_plan_phases_tenant_id", "clinical_treatment_plan_phases", ["tenant_id"])
    op.create_index("ix_clinical_treatment_plan_phases_plan_id", "clinical_treatment_plan_phases", ["plan_id"])
    op.create_index("ix_ctpp_tenant_plan", "clinical_treatment_plan_phases", ["tenant_id", "plan_id"])

    # 5. clinical_treatment_plan_items
    op.create_table(
        "clinical_treatment_plan_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("phase_id", sa.Integer(), sa.ForeignKey("clinical_treatment_plan_phases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_item_id", sa.Integer(), sa.ForeignKey("clinical_work_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_order", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="planned", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("version_id", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("item_order >= 0", name="ck_ctpi_item_order_non_negative"),
        sa.CheckConstraint("length(trim(status)) > 0", name="ck_ctpi_status_not_empty"),
        sa.UniqueConstraint("phase_id", "work_item_id", name="uq_ctpi_phase_work_item"),
        sa.UniqueConstraint("phase_id", "item_order", name="uq_ctpi_phase_item_order"),
    )
    op.create_index("ix_clinical_treatment_plan_items_id", "clinical_treatment_plan_items", ["id"])
    op.create_index("ix_clinical_treatment_plan_items_tenant_id", "clinical_treatment_plan_items", ["tenant_id"])
    op.create_index("ix_clinical_treatment_plan_items_phase_id", "clinical_treatment_plan_items", ["phase_id"])
    op.create_index("ix_clinical_treatment_plan_items_work_item_id", "clinical_treatment_plan_items", ["work_item_id"])
    op.create_index("ix_ctpi_tenant_phase", "clinical_treatment_plan_items", ["tenant_id", "phase_id"])
    op.create_index("ix_ctpi_tenant_work_item", "clinical_treatment_plan_items", ["tenant_id", "work_item_id"])

    # 6. care_sessions
    op.create_table(
        "care_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="in_progress", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("version_id", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(status)) > 0", name="ck_cs_status_not_empty"),
    )
    op.create_index("ix_care_sessions_id", "care_sessions", ["id"])
    op.create_index("ix_care_sessions_tenant_id", "care_sessions", ["tenant_id"])
    op.create_index("ix_care_sessions_patient_id", "care_sessions", ["patient_id"])
    op.create_index("ix_care_sessions_appointment_id", "care_sessions", ["appointment_id"])
    op.create_index("ix_care_sessions_provider_user_id", "care_sessions", ["provider_user_id"])
    op.create_index("ix_cs_tenant_patient", "care_sessions", ["tenant_id", "patient_id"])
    op.create_index("ix_cs_tenant_status", "care_sessions", ["tenant_id", "status"])
    op.create_index("ix_cs_tenant_appointment", "care_sessions", ["tenant_id", "appointment_id"])

    # 7. care_session_steps
    op.create_table(
        "care_session_steps",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("care_session_id", sa.Integer(), sa.ForeignKey("care_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_item_id", sa.Integer(), sa.ForeignKey("clinical_work_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("step_order", sa.Integer(), server_default="1", nullable=False),
        sa.Column("step_code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("version_id", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("step_order >= 0", name="ck_css_step_order_non_negative"),
        sa.CheckConstraint("length(trim(step_code)) > 0", name="ck_css_step_code_not_empty"),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_css_title_not_empty"),
        sa.CheckConstraint("length(trim(status)) > 0", name="ck_css_status_not_empty"),
        sa.UniqueConstraint("care_session_id", "step_order", name="uq_css_session_step_order"),
    )
    op.create_index("ix_care_session_steps_id", "care_session_steps", ["id"])
    op.create_index("ix_care_session_steps_tenant_id", "care_session_steps", ["tenant_id"])
    op.create_index("ix_care_session_steps_care_session_id", "care_session_steps", ["care_session_id"])
    op.create_index("ix_care_session_steps_work_item_id", "care_session_steps", ["work_item_id"])
    op.create_index("ix_css_tenant_session", "care_session_steps", ["tenant_id", "care_session_id"])
    op.create_index("ix_css_tenant_work_item", "care_session_steps", ["tenant_id", "work_item_id"])

    # 8. clinical_events
    op.create_table(
        "clinical_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("work_item_id", sa.Integer(), sa.ForeignKey("clinical_work_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("care_session_id", sa.Integer(), sa.ForeignKey("care_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(event_type)) > 0", name="ck_ce_event_type_not_empty"),
    )
    op.create_index("ix_clinical_events_id", "clinical_events", ["id"])
    op.create_index("ix_clinical_events_tenant_id", "clinical_events", ["tenant_id"])
    op.create_index("ix_clinical_events_patient_id", "clinical_events", ["patient_id"])
    op.create_index("ix_clinical_events_work_item_id", "clinical_events", ["work_item_id"])
    op.create_index("ix_clinical_events_care_session_id", "clinical_events", ["care_session_id"])
    op.create_index("ix_clinical_events_actor_user_id", "clinical_events", ["actor_user_id"])
    op.create_index("ix_clinical_events_occurred_at", "clinical_events", ["occurred_at"])
    op.create_index("ix_ce_tenant_patient_occurred", "clinical_events", ["tenant_id", "patient_id", "occurred_at"])
    op.create_index("ix_ce_tenant_event_type", "clinical_events", ["tenant_id", "event_type"])
    op.create_index("ix_ce_tenant_work_item", "clinical_events", ["tenant_id", "work_item_id"])
    op.create_index("ix_ce_tenant_care_session", "clinical_events", ["tenant_id", "care_session_id"])

    # 9. clinical_event_targets
    op.create_table(
        "clinical_event_targets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("clinical_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_kind", sa.String(length=16), nullable=False),
        sa.Column("tooth_key", sa.String(length=8), nullable=False),
        sa.Column("surface_code", sa.String(length=8), nullable=True),
        sa.Column("root_id", sa.String(length=32), nullable=True),
        sa.Column("canal_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(f"target_kind IN ({TARGET_KIND_CLAUSE})", name="ck_cet_target_kind"),
        sa.CheckConstraint(f"tooth_key IN ({FDI_CLAUSE})", name="ck_cet_tooth_key_fdi"),
        sa.CheckConstraint(f"surface_code IS NULL OR surface_code IN ({SURFACE_CLAUSE})", name="ck_cet_surface_code"),
        sa.CheckConstraint(f"root_id IS NULL OR root_id IN ({ROOT_CLAUSE})", name="ck_cet_root_id"),
        sa.CheckConstraint("canal_id IS NULL OR length(trim(canal_id)) > 0", name="ck_cet_canal_id_not_empty"),
        sa.CheckConstraint(TARGET_SHAPE_CONSTRAINT, name="ck_cet_shape"),
    )
    op.create_index("ix_clinical_event_targets_id", "clinical_event_targets", ["id"])
    op.create_index("ix_clinical_event_targets_tenant_id", "clinical_event_targets", ["tenant_id"])
    op.create_index("ix_clinical_event_targets_event_id", "clinical_event_targets", ["event_id"])
    op.create_index("ix_cet_tenant_event", "clinical_event_targets", ["tenant_id", "event_id"])
    op.create_index(
        "uq_cet_parent_target_exact",
        "clinical_event_targets",
        [
            "event_id",
            "target_kind",
            "tooth_key",
            sa.text("COALESCE(surface_code, '')"),
            sa.text("COALESCE(root_id, '')"),
            sa.text("COALESCE(canal_id, '')"),
        ],
        unique=True,
    )

    # 10. care_observations
    op.create_table(
        "care_observations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("care_session_id", sa.Integer(), sa.ForeignKey("care_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_id", sa.Integer(), sa.ForeignKey("care_session_steps.id", ondelete="SET NULL"), nullable=True),
        sa.Column("work_item_id", sa.Integer(), sa.ForeignKey("clinical_work_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("observation_code", sa.String(length=64), nullable=False),
        sa.Column("tooth_key", sa.String(length=8), nullable=True),
        sa.Column("structured_value", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("recorded_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(observation_code)) > 0", name="ck_co_code_not_empty"),
        sa.CheckConstraint(f"tooth_key IS NULL OR tooth_key IN ({FDI_CLAUSE})", name="ck_co_tooth_key_fdi"),
    )
    op.create_index("ix_care_observations_id", "care_observations", ["id"])
    op.create_index("ix_care_observations_tenant_id", "care_observations", ["tenant_id"])
    op.create_index("ix_care_observations_patient_id", "care_observations", ["patient_id"])
    op.create_index("ix_care_observations_care_session_id", "care_observations", ["care_session_id"])
    op.create_index("ix_care_observations_step_id", "care_observations", ["step_id"])
    op.create_index("ix_care_observations_work_item_id", "care_observations", ["work_item_id"])
    op.create_index("ix_care_observations_recorded_by_user_id", "care_observations", ["recorded_by_user_id"])
    op.create_index("ix_co_tenant_session", "care_observations", ["tenant_id", "care_session_id"])
    op.create_index("ix_co_tenant_patient", "care_observations", ["tenant_id", "patient_id"])
    op.create_index("ix_co_tenant_step", "care_observations", ["tenant_id", "step_id"])
    op.create_index("ix_co_tenant_work_item", "care_observations", ["tenant_id", "work_item_id"])

    # 11. workflow_templates
    op.create_table(
        "workflow_templates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("template_code", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(template_code)) > 0", name="ck_wt_template_code_not_empty"),
        sa.CheckConstraint("version > 0", name="ck_wt_version_positive"),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_wt_title_not_empty"),
        sa.UniqueConstraint("tenant_id", "template_code", "version", name="uq_wt_tenant_code_version"),
    )
    op.create_index("ix_workflow_templates_id", "workflow_templates", ["id"])
    op.create_index("ix_workflow_templates_tenant_id", "workflow_templates", ["tenant_id"])
    op.create_index("ix_wt_tenant_active", "workflow_templates", ["tenant_id", "is_active"])

    # 12. next_visit_requests
    op.create_table(
        "next_visit_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("care_session_id", sa.Integer(), sa.ForeignKey("care_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("work_item_id", sa.Integer(), sa.ForeignKey("clinical_work_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("requested_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("suggested_duration_minutes", sa.Integer(), server_default="30", nullable=False),
        sa.Column("preferred_time_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("preferred_time_window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="requested", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(reason)) > 0", name="ck_nvr_reason_not_empty"),
        sa.CheckConstraint("suggested_duration_minutes > 0", name="ck_nvr_duration_positive"),
        sa.CheckConstraint("length(trim(status)) > 0", name="ck_nvr_status_not_empty"),
    )
    op.create_index("ix_next_visit_requests_id", "next_visit_requests", ["id"])
    op.create_index("ix_next_visit_requests_tenant_id", "next_visit_requests", ["tenant_id"])
    op.create_index("ix_next_visit_requests_patient_id", "next_visit_requests", ["patient_id"])
    op.create_index("ix_next_visit_requests_care_session_id", "next_visit_requests", ["care_session_id"])
    op.create_index("ix_next_visit_requests_work_item_id", "next_visit_requests", ["work_item_id"])
    op.create_index("ix_next_visit_requests_requested_by_user_id", "next_visit_requests", ["requested_by_user_id"])
    op.create_index("ix_nvr_tenant_patient", "next_visit_requests", ["tenant_id", "patient_id"])
    op.create_index("ix_nvr_tenant_status", "next_visit_requests", ["tenant_id", "status"])
    op.create_index("ix_nvr_tenant_care_session", "next_visit_requests", ["tenant_id", "care_session_id"])
    op.create_index("ix_nvr_tenant_work_item", "next_visit_requests", ["tenant_id", "work_item_id"])

    # 13. clinical_attachment_links
    op.create_table(
        "clinical_attachment_links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("attachment_id", sa.Integer(), sa.ForeignKey("attachments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("work_item_id", sa.Integer(), sa.ForeignKey("clinical_work_items.id", ondelete="CASCADE"), nullable=True),
        sa.Column("care_session_id", sa.Integer(), sa.ForeignKey("care_sessions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("clinical_event_id", sa.Integer(), sa.ForeignKey("clinical_events.id", ondelete="CASCADE"), nullable=True),
        sa.Column("tooth_key", sa.String(length=8), nullable=True),
        sa.Column("purpose_code", sa.String(length=64), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(purpose_code)) > 0", name="ck_cal_purpose_code_not_empty"),
        sa.CheckConstraint(f"tooth_key IS NULL OR tooth_key IN ({FDI_CLAUSE})", name="ck_cal_tooth_key_fdi"),
        sa.CheckConstraint(
            "work_item_id IS NOT NULL OR care_session_id IS NOT NULL OR clinical_event_id IS NOT NULL OR tooth_key IS NOT NULL",
            name="ck_cal_clinical_context_required",
        ),
    )
    op.create_index("ix_clinical_attachment_links_id", "clinical_attachment_links", ["id"])
    op.create_index("ix_clinical_attachment_links_tenant_id", "clinical_attachment_links", ["tenant_id"])
    op.create_index("ix_clinical_attachment_links_attachment_id", "clinical_attachment_links", ["attachment_id"])
    op.create_index("ix_clinical_attachment_links_patient_id", "clinical_attachment_links", ["patient_id"])
    op.create_index("ix_clinical_attachment_links_work_item_id", "clinical_attachment_links", ["work_item_id"])
    op.create_index("ix_clinical_attachment_links_care_session_id", "clinical_attachment_links", ["care_session_id"])
    op.create_index("ix_clinical_attachment_links_clinical_event_id", "clinical_attachment_links", ["clinical_event_id"])
    op.create_index("ix_cal_tenant_patient", "clinical_attachment_links", ["tenant_id", "patient_id"])
    op.create_index("ix_cal_tenant_attachment", "clinical_attachment_links", ["tenant_id", "attachment_id"])
    op.create_index("ix_cal_tenant_work_item", "clinical_attachment_links", ["tenant_id", "work_item_id"])
    op.create_index("ix_cal_tenant_care_session", "clinical_attachment_links", ["tenant_id", "care_session_id"])
    op.create_index("ix_cal_tenant_clinical_event", "clinical_attachment_links", ["tenant_id", "clinical_event_id"])
    op.create_index(
        "uq_cal_attachment_context_exact",
        "clinical_attachment_links",
        [
            "attachment_id",
            sa.text("COALESCE(work_item_id, 0)"),
            sa.text("COALESCE(care_session_id, 0)"),
            sa.text("COALESCE(clinical_event_id, 0)"),
            sa.text("COALESCE(tooth_key, '')"),
        ],
        unique=True,
    )

    # PostgreSQL-specific RLS and parent-tenant / parent-patient triggers
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        tenant_expr = "tenant_id = NULLIF(current_setting('rls.tenant_id', true), '')::integer"
        for table in NEW_TABLES:
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
            """
            CREATE OR REPLACE FUNCTION dentix_assert_parent_tenant()
            RETURNS trigger LANGUAGE plpgsql AS $$
            DECLARE
                child_parent_id integer;
                parent_tenant_id integer;
                allow_null boolean := COALESCE(TG_ARGV[2], 'false')::boolean;
            BEGIN
                child_parent_id := NULLIF(to_jsonb(NEW) ->> TG_ARGV[1], '')::integer;
                IF child_parent_id IS NULL AND allow_null THEN RETURN NEW; END IF;
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

        for table, child_key, parent, allow_null in NEW_CHILD_TENANT_RELATIONSHIPS:
            trigger = _trigger_name(table, child_key)
            op.execute(f'DROP TRIGGER IF EXISTS "{trigger}" ON "{table}"')
            op.execute(
                f'''CREATE TRIGGER "{trigger}"
                    BEFORE INSERT OR UPDATE OF tenant_id, "{child_key}" ON "{table}"
                    FOR EACH ROW EXECUTE FUNCTION dentix_assert_parent_tenant(
                        '{parent}', '{child_key}', '{str(allow_null).lower()}'
                    )'''
            )

        # Cross-patient defense-in-depth: direct parent patient verification
        op.execute(
            """
            CREATE OR REPLACE FUNCTION dentix_assert_parent_patient()
            RETURNS trigger LANGUAGE plpgsql AS $$
            DECLARE
                child_parent_id integer;
                parent_patient_id integer;
                allow_null boolean := COALESCE(TG_ARGV[2], 'false')::boolean;
            BEGIN
                child_parent_id := NULLIF(to_jsonb(NEW) ->> TG_ARGV[1], '')::integer;
                IF child_parent_id IS NULL AND allow_null THEN RETURN NEW; END IF;
                IF child_parent_id IS NULL THEN
                    RAISE EXCEPTION 'Missing required parent on % for %', TG_TABLE_NAME, TG_ARGV[1];
                END IF;
                EXECUTE format('SELECT patient_id FROM %I WHERE id = $1', TG_ARGV[0])
                   INTO parent_patient_id USING child_parent_id;
                IF parent_patient_id IS NULL THEN
                    RAISE EXCEPTION 'Referenced parent % % not found for %', TG_ARGV[0], child_parent_id, TG_TABLE_NAME;
                END IF;
                IF NEW.patient_id IS DISTINCT FROM parent_patient_id THEN
                    RAISE EXCEPTION 'Patient mismatch on %: row patient % != parent % patient %',
                        TG_TABLE_NAME, NEW.patient_id, TG_ARGV[0], parent_patient_id;
                END IF;
                RETURN NEW;
            END;
            $$
            """
        )

        for table, child_key, parent, allow_null in NEW_CHILD_PATIENT_RELATIONSHIPS:
            trigger = _patient_trigger_name(table, child_key)
            op.execute(f'DROP TRIGGER IF EXISTS "{trigger}" ON "{table}"')
            op.execute(
                f'''CREATE TRIGGER "{trigger}"
                    BEFORE INSERT OR UPDATE OF patient_id, "{child_key}" ON "{table}"
                    FOR EACH ROW EXECUTE FUNCTION dentix_assert_parent_patient(
                        '{parent}', '{child_key}', '{str(allow_null).lower()}'
                    )'''
            )

        # Specialized relational traversal cross-patient checks:
        # 1. clinical_treatment_plan_items: phase plan patient == work_item patient
        op.execute(
            """
            CREATE OR REPLACE FUNCTION dentix_assert_ctpi_patient()
            RETURNS trigger LANGUAGE plpgsql AS $$
            DECLARE
                v_plan_patient_id integer;
                v_work_item_patient_id integer;
            BEGIN
                SELECT p.patient_id INTO v_plan_patient_id
                  FROM clinical_treatment_plan_phases ph
                  JOIN clinical_treatment_plans p ON p.id = ph.plan_id
                 WHERE ph.id = NEW.phase_id;
                IF v_plan_patient_id IS NULL THEN
                    RAISE EXCEPTION 'Referenced treatment plan phase % not found for clinical_treatment_plan_items', NEW.phase_id;
                END IF;
                SELECT patient_id INTO v_work_item_patient_id
                  FROM clinical_work_items
                 WHERE id = NEW.work_item_id;
                IF v_work_item_patient_id IS NULL THEN
                    RAISE EXCEPTION 'Referenced work item % not found for clinical_treatment_plan_items', NEW.work_item_id;
                END IF;
                IF v_plan_patient_id IS DISTINCT FROM v_work_item_patient_id THEN
                    RAISE EXCEPTION 'Patient mismatch on clinical_treatment_plan_items: plan patient % != work item patient %',
                        v_plan_patient_id, v_work_item_patient_id;
                END IF;
                RETURN NEW;
            END;
            $$
            """
        )
        op.execute('DROP TRIGGER IF EXISTS "trg_ctpi_phase_work_item_patient" ON "clinical_treatment_plan_items"')
        op.execute(
            """
            CREATE TRIGGER "trg_ctpi_phase_work_item_patient"
            BEFORE INSERT OR UPDATE OF phase_id, work_item_id ON "clinical_treatment_plan_items"
            FOR EACH ROW EXECUTE FUNCTION dentix_assert_ctpi_patient()
            """
        )

        # 2. care_session_steps: session patient == work_item patient
        op.execute(
            """
            CREATE OR REPLACE FUNCTION dentix_assert_css_patient()
            RETURNS trigger LANGUAGE plpgsql AS $$
            DECLARE
                v_session_patient_id integer;
                v_work_item_patient_id integer;
            BEGIN
                IF NEW.work_item_id IS NULL THEN
                    RETURN NEW;
                END IF;
                SELECT patient_id INTO v_session_patient_id
                  FROM care_sessions
                 WHERE id = NEW.care_session_id;
                IF v_session_patient_id IS NULL THEN
                    RAISE EXCEPTION 'Referenced care session % not found for care_session_steps', NEW.care_session_id;
                END IF;
                SELECT patient_id INTO v_work_item_patient_id
                  FROM clinical_work_items
                 WHERE id = NEW.work_item_id;
                IF v_work_item_patient_id IS NULL THEN
                    RAISE EXCEPTION 'Referenced work item % not found for care_session_steps', NEW.work_item_id;
                END IF;
                IF v_session_patient_id IS DISTINCT FROM v_work_item_patient_id THEN
                    RAISE EXCEPTION 'Patient mismatch on care_session_steps: session patient % != work item patient %',
                        v_session_patient_id, v_work_item_patient_id;
                END IF;
                RETURN NEW;
            END;
            $$
            """
        )
        op.execute('DROP TRIGGER IF EXISTS "trg_css_session_work_item_patient" ON "care_session_steps"')
        op.execute(
            """
            CREATE TRIGGER "trg_css_session_work_item_patient"
            BEFORE INSERT OR UPDATE OF care_session_id, work_item_id ON "care_session_steps"
            FOR EACH ROW EXECUTE FUNCTION dentix_assert_css_patient()
            """
        )

        # 3. care_observations: step care_session_id == observation care_session_id
        op.execute(
            """
            CREATE OR REPLACE FUNCTION dentix_assert_co_step_session()
            RETURNS trigger LANGUAGE plpgsql AS $$
            DECLARE
                v_step_session_id integer;
            BEGIN
                IF NEW.step_id IS NULL THEN
                    RETURN NEW;
                END IF;
                SELECT care_session_id INTO v_step_session_id
                  FROM care_session_steps
                 WHERE id = NEW.step_id;
                IF v_step_session_id IS NULL THEN
                    RAISE EXCEPTION 'Referenced care session step % not found for care_observations', NEW.step_id;
                END IF;
                IF v_step_session_id IS DISTINCT FROM NEW.care_session_id THEN
                    RAISE EXCEPTION 'Care session mismatch on care_observations: step % belongs to session %, not %',
                        NEW.step_id, v_step_session_id, NEW.care_session_id;
                END IF;
                RETURN NEW;
            END;
            $$
            """
        )
        op.execute('DROP TRIGGER IF EXISTS "trg_co_step_care_session_match" ON "care_observations"')
        op.execute(
            """
            CREATE TRIGGER "trg_co_step_care_session_match"
            BEFORE INSERT OR UPDATE OF care_session_id, step_id ON "care_observations"
            FOR EACH ROW EXECUTE FUNCTION dentix_assert_co_step_session()
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Drop specialized cross-patient triggers
        for table, trigger in reversed(SPECIALIZED_G1_PATIENT_TRIGGERS):
            op.execute(f'DROP TRIGGER IF EXISTS "{trigger}" ON "{table}"')

        # Drop direct parent-patient triggers
        for table, child_key, _, _ in reversed(NEW_CHILD_PATIENT_RELATIONSHIPS):
            trigger = _patient_trigger_name(table, child_key)
            op.execute(f'DROP TRIGGER IF EXISTS "{trigger}" ON "{table}"')

        # Drop patient integrity functions
        op.execute("DROP FUNCTION IF EXISTS dentix_assert_co_step_session()")
        op.execute("DROP FUNCTION IF EXISTS dentix_assert_css_patient()")
        op.execute("DROP FUNCTION IF EXISTS dentix_assert_ctpi_patient()")
        op.execute("DROP FUNCTION IF EXISTS dentix_assert_parent_patient()")

        # Drop same-tenant triggers
        for table, child_key, _, _ in reversed(NEW_CHILD_TENANT_RELATIONSHIPS):
            trigger = _trigger_name(table, child_key)
            op.execute(f'DROP TRIGGER IF EXISTS "{trigger}" ON "{table}"')

        # Drop RLS policies
        for table in reversed(NEW_TABLES):
            op.execute(f'DROP POLICY IF EXISTS "{table}_tenant_policy" ON "{table}"')

    # Drop tables in exact reverse dependency order
    for table in reversed(NEW_TABLES):
        op.drop_table(table)
