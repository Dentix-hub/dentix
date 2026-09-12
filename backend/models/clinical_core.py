"""
Clinical VNext Core Models (Phase G1)

Normalized additive clinical tables:
- clinical_work_items
- clinical_work_item_targets
- clinical_treatment_plans
- clinical_treatment_plan_phases
- clinical_treatment_plan_items
- clinical_events
- clinical_event_targets
- care_sessions
- care_session_steps
- care_observations
- workflow_templates
- next_visit_requests
- clinical_attachment_links

All tables enforce tenant ownership, RLS policies, explicit integer PK/FKs,
deterministic constraint naming, and portable FDI/shape validation.
"""

from rls.schemas import Command, ConditionArg, Permissive
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    column,
    func,
    true,
)
from sqlalchemy.orm import relationship

from .base import Base

# Canonical 52 FDI Tooth Keys (32 permanent + 20 primary)
FDI_TOOTH_KEYS: tuple[str, ...] = (
    # Permanent dentition (quadrants 1-4, positions 1-8)
    "11", "12", "13", "14", "15", "16", "17", "18",
    "21", "22", "23", "24", "25", "26", "27", "28",
    "31", "32", "33", "34", "35", "36", "37", "38",
    "41", "42", "43", "44", "45", "46", "47", "48",
    # Primary dentition (quadrants 5-8, positions 1-5)
    "51", "52", "53", "54", "55",
    "61", "62", "63", "64", "65",
    "71", "72", "73", "74", "75",
    "81", "82", "83", "84", "85",
)

FDI_CLAUSE = ", ".join(f"'{k}'" for k in FDI_TOOTH_KEYS)

SURFACE_CODES: tuple[str, ...] = ("M", "D", "O", "I", "B", "L", "P")
SURFACE_CLAUSE = ", ".join(f"'{s}'" for s in SURFACE_CODES)

ROOT_IDS: tuple[str, ...] = (
    "single",
    "buccal",
    "palatal",
    "mesiobuccal",
    "distobuccal",
    "mesial",
    "distal",
)
ROOT_CLAUSE = ", ".join(f"'{r}'" for r in ROOT_IDS)

TARGET_KINDS: tuple[str, ...] = ("tooth", "surface", "root", "canal")
TARGET_KIND_CLAUSE = ", ".join(f"'{k}'" for k in TARGET_KINDS)

TARGET_SHAPE_CONSTRAINT = (
    "("
    "(target_kind = 'tooth' AND surface_code IS NULL AND root_id IS NULL AND canal_id IS NULL) OR "
    "(target_kind = 'surface' AND surface_code IS NOT NULL AND root_id IS NULL AND canal_id IS NULL) OR "
    "(target_kind = 'root' AND surface_code IS NULL AND root_id IS NOT NULL AND canal_id IS NULL) OR "
    "(target_kind = 'canal' AND surface_code IS NULL AND root_id IS NOT NULL)"
    ")"
)


def _tenant_rls_policy():
    return [
        Permissive(
            condition_args=[ConditionArg(comparator_name="tenant_id", type=Integer)],
            cmd=[Command.select, Command.update, Command.delete, Command.insert],
            custom_expr=lambda x: column("tenant_id") == x,
        )
    ]


class ClinicalWorkItem(Base):
    """
    Core clinical work item: represents a clinical finding or procedure.
    Work items can be associated with multiple treatment plans via
    clinical_treatment_plan_items without data duplication.
    """
    __tablename__ = "clinical_work_items"

    __rls_policies__ = _tenant_rls_policy()

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    kind = Column(String(32), nullable=False)
    code = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="proposed", server_default="proposed")
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    version_id = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("kind IN ('finding', 'procedure')", name="ck_clinical_work_items_kind"),
        CheckConstraint("length(trim(code)) > 0", name="ck_clinical_work_items_code_not_empty"),
        CheckConstraint("length(trim(status)) > 0", name="ck_clinical_work_items_status_not_empty"),
        Index("ix_clinical_work_items_tenant_patient", "tenant_id", "patient_id"),
        Index("ix_clinical_work_items_tenant_kind", "tenant_id", "kind"),
        Index("ix_clinical_work_items_tenant_status", "tenant_id", "status"),
    )

    __mapper_args__ = {
        "version_id_col": version_id,
    }

    patient = relationship("Patient")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    targets = relationship(
        "ClinicalWorkItemTarget",
        back_populates="work_item",
        cascade="all, delete-orphan",
    )
    plan_items = relationship("ClinicalTreatmentPlanItem", back_populates="work_item")
    events = relationship("ClinicalEvent", back_populates="work_item")
    session_steps = relationship("CareSessionStep", back_populates="work_item")
    observations = relationship("CareObservation", back_populates="work_item")
    next_visit_requests = relationship("NextVisitRequest", back_populates="work_item")
    attachment_links = relationship("ClinicalAttachmentLink", back_populates="work_item")


class ClinicalWorkItemTarget(Base):
    """
    Anatomical target for a clinical work item: tooth, surface, root, or canal.
    Enforces per-kind shape and FDI 2-digit structural validation.
    """
    __tablename__ = "clinical_work_item_targets"

    __rls_policies__ = _tenant_rls_policy()

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    work_item_id = Column(Integer, ForeignKey("clinical_work_items.id", ondelete="CASCADE"), nullable=False, index=True)
    target_kind = Column(String(16), nullable=False)
    tooth_key = Column(String(8), nullable=False)
    surface_code = Column(String(8), nullable=True)
    root_id = Column(String(32), nullable=True)
    canal_id = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(f"target_kind IN ({TARGET_KIND_CLAUSE})", name="ck_cwit_target_kind"),
        CheckConstraint(f"tooth_key IN ({FDI_CLAUSE})", name="ck_cwit_tooth_key_fdi"),
        CheckConstraint(f"surface_code IS NULL OR surface_code IN ({SURFACE_CLAUSE})", name="ck_cwit_surface_code"),
        CheckConstraint(f"root_id IS NULL OR root_id IN ({ROOT_CLAUSE})", name="ck_cwit_root_id"),
        CheckConstraint("canal_id IS NULL OR length(trim(canal_id)) > 0", name="ck_cwit_canal_id_not_empty"),
        CheckConstraint(TARGET_SHAPE_CONSTRAINT, name="ck_cwit_shape"),
        Index("ix_cwit_tenant_work_item", "tenant_id", "work_item_id"),
        Index(
            "uq_cwit_parent_target_exact",
            "work_item_id",
            "target_kind",
            "tooth_key",
            func.coalesce(column("surface_code"), ""),
            func.coalesce(column("root_id"), ""),
            func.coalesce(column("canal_id"), ""),
            unique=True,
        ),
    )

    work_item = relationship("ClinicalWorkItem", back_populates="targets")


class ClinicalTreatmentPlan(Base):
    """
    Patient-level treatment plan composed of sequential or grouped phases.
    """
    __tablename__ = "clinical_treatment_plans"

    __rls_policies__ = _tenant_rls_policy()

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="draft", server_default="draft")
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    version_id = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="ck_ctp_title_not_empty"),
        CheckConstraint("length(trim(status)) > 0", name="ck_ctp_status_not_empty"),
        Index("ix_ctp_tenant_patient", "tenant_id", "patient_id"),
        Index("ix_ctp_tenant_status", "tenant_id", "status"),
    )

    __mapper_args__ = {
        "version_id_col": version_id,
    }

    patient = relationship("Patient")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    phases = relationship(
        "ClinicalTreatmentPlanPhase",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="ClinicalTreatmentPlanPhase.phase_order",
    )


class ClinicalTreatmentPlanPhase(Base):
    """
    Ordered phase inside a treatment plan (e.g. Phase 1: Urgent, Phase 2: Restorative).
    """
    __tablename__ = "clinical_treatment_plan_phases"

    __rls_policies__ = _tenant_rls_policy()

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("clinical_treatment_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    phase_order = Column(Integer, nullable=False, default=1, server_default="1")
    name = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="draft", server_default="draft")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("phase_order >= 0", name="ck_ctpp_phase_order_non_negative"),
        CheckConstraint("length(trim(name)) > 0", name="ck_ctpp_name_not_empty"),
        CheckConstraint("length(trim(status)) > 0", name="ck_ctpp_status_not_empty"),
        UniqueConstraint("plan_id", "phase_order", name="uq_ctpp_plan_phase_order"),
        Index("ix_ctpp_tenant_plan", "tenant_id", "plan_id"),
    )

    plan = relationship("ClinicalTreatmentPlan", back_populates="phases")
    items = relationship(
        "ClinicalTreatmentPlanItem",
        back_populates="phase",
        cascade="all, delete-orphan",
        order_by="ClinicalTreatmentPlanItem.item_order",
    )


class ClinicalTreatmentPlanItem(Base):
    """
    Association linking an existing clinical_work_items row into a treatment plan phase.
    Work items can be shared across multiple alternative plans without duplication.
    """
    __tablename__ = "clinical_treatment_plan_items"

    __rls_policies__ = _tenant_rls_policy()

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    phase_id = Column(Integer, ForeignKey("clinical_treatment_plan_phases.id", ondelete="CASCADE"), nullable=False, index=True)
    work_item_id = Column(Integer, ForeignKey("clinical_work_items.id", ondelete="CASCADE"), nullable=False, index=True)
    item_order = Column(Integer, nullable=False, default=1, server_default="1")
    status = Column(String(32), nullable=False, default="planned", server_default="planned")
    notes = Column(Text, nullable=True)
    version_id = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("item_order >= 0", name="ck_ctpi_item_order_non_negative"),
        CheckConstraint("length(trim(status)) > 0", name="ck_ctpi_status_not_empty"),
        UniqueConstraint("phase_id", "work_item_id", name="uq_ctpi_phase_work_item"),
        UniqueConstraint("phase_id", "item_order", name="uq_ctpi_phase_item_order"),
        Index("ix_ctpi_tenant_phase", "tenant_id", "phase_id"),
        Index("ix_ctpi_tenant_work_item", "tenant_id", "work_item_id"),
    )

    __mapper_args__ = {
        "version_id_col": version_id,
    }

    phase = relationship("ClinicalTreatmentPlanPhase", back_populates="items")
    work_item = relationship("ClinicalWorkItem", back_populates="plan_items")


class ClinicalEvent(Base):
    """
    Append-oriented clinical event log / clinical history.
    Distinct from infrastructure domain_events (outbox pattern).
    """
    __tablename__ = "clinical_events"

    __rls_policies__ = _tenant_rls_policy()

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    work_item_id = Column(Integer, ForeignKey("clinical_work_items.id", ondelete="SET NULL"), nullable=True, index=True)
    care_session_id = Column(Integer, ForeignKey("care_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(64), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("length(trim(event_type)) > 0", name="ck_ce_event_type_not_empty"),
        Index("ix_ce_tenant_patient_occurred", "tenant_id", "patient_id", "occurred_at"),
        Index("ix_ce_tenant_event_type", "tenant_id", "event_type"),
        Index("ix_ce_tenant_work_item", "tenant_id", "work_item_id"),
        Index("ix_ce_tenant_care_session", "tenant_id", "care_session_id"),
    )

    patient = relationship("Patient")
    work_item = relationship("ClinicalWorkItem", back_populates="events")
    care_session = relationship("CareSession", back_populates="events")
    actor = relationship("User", foreign_keys=[actor_user_id])
    targets = relationship(
        "ClinicalEventTarget",
        back_populates="event",
        cascade="all, delete-orphan",
    )
    attachment_links = relationship("ClinicalAttachmentLink", back_populates="clinical_event")


class ClinicalEventTarget(Base):
    """
    Anatomical target associated with an append-oriented clinical event.
    """
    __tablename__ = "clinical_event_targets"

    __rls_policies__ = _tenant_rls_policy()

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("clinical_events.id", ondelete="CASCADE"), nullable=False, index=True)
    target_kind = Column(String(16), nullable=False)
    tooth_key = Column(String(8), nullable=False)
    surface_code = Column(String(8), nullable=True)
    root_id = Column(String(32), nullable=True)
    canal_id = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(f"target_kind IN ({TARGET_KIND_CLAUSE})", name="ck_cet_target_kind"),
        CheckConstraint(f"tooth_key IN ({FDI_CLAUSE})", name="ck_cet_tooth_key_fdi"),
        CheckConstraint(f"surface_code IS NULL OR surface_code IN ({SURFACE_CLAUSE})", name="ck_cet_surface_code"),
        CheckConstraint(f"root_id IS NULL OR root_id IN ({ROOT_CLAUSE})", name="ck_cet_root_id"),
        CheckConstraint("canal_id IS NULL OR length(trim(canal_id)) > 0", name="ck_cet_canal_id_not_empty"),
        CheckConstraint(TARGET_SHAPE_CONSTRAINT, name="ck_cet_shape"),
        Index("ix_cet_tenant_event", "tenant_id", "event_id"),
        Index(
            "uq_cet_parent_target_exact",
            "event_id",
            "target_kind",
            "tooth_key",
            func.coalesce(column("surface_code"), ""),
            func.coalesce(column("root_id"), ""),
            func.coalesce(column("canal_id"), ""),
            unique=True,
        ),
    )

    event = relationship("ClinicalEvent", back_populates="targets")


class CareSession(Base):
    """
    Clinical care encounter/session conducted chairside with a patient.
    """
    __tablename__ = "care_sessions"

    __rls_policies__ = _tenant_rls_policy()

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True, index=True)
    provider_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    status = Column(String(32), nullable=False, default="in_progress", server_default="in_progress")
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    version_id = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("length(trim(status)) > 0", name="ck_cs_status_not_empty"),
        Index("ix_cs_tenant_patient", "tenant_id", "patient_id"),
        Index("ix_cs_tenant_status", "tenant_id", "status"),
        Index("ix_cs_tenant_appointment", "tenant_id", "appointment_id"),
    )

    __mapper_args__ = {
        "version_id_col": version_id,
    }

    patient = relationship("Patient")
    appointment = relationship("Appointment")
    provider = relationship("User", foreign_keys=[provider_user_id])
    steps = relationship(
        "CareSessionStep",
        back_populates="care_session",
        cascade="all, delete-orphan",
        order_by="CareSessionStep.step_order",
    )
    observations = relationship(
        "CareObservation",
        back_populates="care_session",
        cascade="all, delete-orphan",
    )
    events = relationship("ClinicalEvent", back_populates="care_session")
    next_visit_requests = relationship("NextVisitRequest", back_populates="care_session")
    attachment_links = relationship("ClinicalAttachmentLink", back_populates="care_session")


class CareSessionStep(Base):
    """
    Ordered structured step performed within an active care session.
    """
    __tablename__ = "care_session_steps"

    __rls_policies__ = _tenant_rls_policy()

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    care_session_id = Column(Integer, ForeignKey("care_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    work_item_id = Column(Integer, ForeignKey("clinical_work_items.id", ondelete="SET NULL"), nullable=True, index=True)
    step_order = Column(Integer, nullable=False, default=1, server_default="1")
    step_code = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="pending", server_default="pending")
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    version_id = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("step_order >= 0", name="ck_css_step_order_non_negative"),
        CheckConstraint("length(trim(step_code)) > 0", name="ck_css_step_code_not_empty"),
        CheckConstraint("length(trim(title)) > 0", name="ck_css_title_not_empty"),
        CheckConstraint("length(trim(status)) > 0", name="ck_css_status_not_empty"),
        UniqueConstraint("care_session_id", "step_order", name="uq_css_session_step_order"),
        Index("ix_css_tenant_session", "tenant_id", "care_session_id"),
        Index("ix_css_tenant_work_item", "tenant_id", "work_item_id"),
    )

    __mapper_args__ = {
        "version_id_col": version_id,
    }

    care_session = relationship("CareSession", back_populates="steps")
    work_item = relationship("ClinicalWorkItem", back_populates="session_steps")
    observations = relationship("CareObservation", back_populates="step")


class CareObservation(Base):
    """
    Structured chairside observation or measurement recorded during a care session.
    """
    __tablename__ = "care_observations"

    __rls_policies__ = _tenant_rls_policy()

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    care_session_id = Column(Integer, ForeignKey("care_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    step_id = Column(Integer, ForeignKey("care_session_steps.id", ondelete="SET NULL"), nullable=True, index=True)
    work_item_id = Column(Integer, ForeignKey("clinical_work_items.id", ondelete="SET NULL"), nullable=True, index=True)
    observation_code = Column(String(64), nullable=False)
    tooth_key = Column(String(8), nullable=True)
    structured_value = Column(JSON, nullable=False, default=dict)
    notes = Column(Text, nullable=True)
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now())
    recorded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("length(trim(observation_code)) > 0", name="ck_co_code_not_empty"),
        CheckConstraint(f"tooth_key IS NULL OR tooth_key IN ({FDI_CLAUSE})", name="ck_co_tooth_key_fdi"),
        Index("ix_co_tenant_session", "tenant_id", "care_session_id"),
        Index("ix_co_tenant_patient", "tenant_id", "patient_id"),
        Index("ix_co_tenant_step", "tenant_id", "step_id"),
        Index("ix_co_tenant_work_item", "tenant_id", "work_item_id"),
    )

    patient = relationship("Patient")
    care_session = relationship("CareSession", back_populates="observations")
    step = relationship("CareSessionStep", back_populates="observations")
    work_item = relationship("ClinicalWorkItem", back_populates="observations")
    recorded_by = relationship("User", foreign_keys=[recorded_by_user_id])


class WorkflowTemplate(Base):
    """
    Tenant-owned, versionable clinical workflow template defining step blueprints.
    """
    __tablename__ = "workflow_templates"

    __rls_policies__ = _tenant_rls_policy()

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    template_code = Column(String(64), nullable=False)
    version = Column(Integer, nullable=False, default=1, server_default="1")
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default=true())
    definition = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("length(trim(template_code)) > 0", name="ck_wt_template_code_not_empty"),
        CheckConstraint("version > 0", name="ck_wt_version_positive"),
        CheckConstraint("length(trim(title)) > 0", name="ck_wt_title_not_empty"),
        UniqueConstraint("tenant_id", "template_code", "version", name="uq_wt_tenant_code_version"),
        Index("ix_wt_tenant_active", "tenant_id", "is_active"),
    )


class NextVisitRequest(Base):
    """
    Request for next appointment or follow-up visit queued chairside for reception.
    Never auto-books an appointment without explicit confirmed front-desk action.
    """
    __tablename__ = "next_visit_requests"

    __rls_policies__ = _tenant_rls_policy()

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    care_session_id = Column(Integer, ForeignKey("care_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    work_item_id = Column(Integer, ForeignKey("clinical_work_items.id", ondelete="SET NULL"), nullable=True, index=True)
    requested_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    reason = Column(String(255), nullable=False)
    suggested_duration_minutes = Column(Integer, nullable=False, default=30, server_default="30")
    preferred_time_window_start = Column(DateTime(timezone=True), nullable=True)
    preferred_time_window_end = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), nullable=False, default="requested", server_default="requested")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("length(trim(reason)) > 0", name="ck_nvr_reason_not_empty"),
        CheckConstraint("suggested_duration_minutes > 0", name="ck_nvr_duration_positive"),
        CheckConstraint("length(trim(status)) > 0", name="ck_nvr_status_not_empty"),
        Index("ix_nvr_tenant_patient", "tenant_id", "patient_id"),
        Index("ix_nvr_tenant_status", "tenant_id", "status"),
        Index("ix_nvr_tenant_care_session", "tenant_id", "care_session_id"),
        Index("ix_nvr_tenant_work_item", "tenant_id", "work_item_id"),
    )

    patient = relationship("Patient")
    care_session = relationship("CareSession", back_populates="next_visit_requests")
    work_item = relationship("ClinicalWorkItem", back_populates="next_visit_requests")
    requested_by = relationship("User", foreign_keys=[requested_by_user_id])


class ClinicalAttachmentLink(Base):
    """
    Contextual link associating an existing attachment with clinical contexts
    (work item, care session, clinical event, or tooth).
    Requires at least one clinical context and preserves existing attachments untouched.
    """
    __tablename__ = "clinical_attachment_links"

    __rls_policies__ = _tenant_rls_policy()

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    attachment_id = Column(Integer, ForeignKey("attachments.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    work_item_id = Column(Integer, ForeignKey("clinical_work_items.id", ondelete="CASCADE"), nullable=True, index=True)
    care_session_id = Column(Integer, ForeignKey("care_sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    clinical_event_id = Column(Integer, ForeignKey("clinical_events.id", ondelete="CASCADE"), nullable=True, index=True)
    tooth_key = Column(String(8), nullable=True)
    purpose_code = Column(String(64), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("length(trim(purpose_code)) > 0", name="ck_cal_purpose_code_not_empty"),
        CheckConstraint(f"tooth_key IS NULL OR tooth_key IN ({FDI_CLAUSE})", name="ck_cal_tooth_key_fdi"),
        CheckConstraint(
            "work_item_id IS NOT NULL OR care_session_id IS NOT NULL OR clinical_event_id IS NOT NULL OR tooth_key IS NOT NULL",
            name="ck_cal_clinical_context_required",
        ),
        Index("ix_cal_tenant_patient", "tenant_id", "patient_id"),
        Index("ix_cal_tenant_attachment", "tenant_id", "attachment_id"),
        Index("ix_cal_tenant_work_item", "tenant_id", "work_item_id"),
        Index("ix_cal_tenant_care_session", "tenant_id", "care_session_id"),
        Index("ix_cal_tenant_clinical_event", "tenant_id", "clinical_event_id"),
        Index(
            "uq_cal_attachment_context_exact",
            "attachment_id",
            func.coalesce(column("work_item_id"), 0),
            func.coalesce(column("care_session_id"), 0),
            func.coalesce(column("clinical_event_id"), 0),
            func.coalesce(column("tooth_key"), ""),
            unique=True,
        ),
    )

    attachment = relationship("Attachment")
    patient = relationship("Patient")
    work_item = relationship("ClinicalWorkItem", back_populates="attachment_links")
    care_session = relationship("CareSession", back_populates="attachment_links")
    clinical_event = relationship("ClinicalEvent", back_populates="attachment_links")


COVERAGE_DOMAINS: tuple[str, ...] = ("teeth", "treatments", "sessions")
COVERAGE_STATES: tuple[str, ...] = ("UNCOVERED", "PARTIAL", "COMPLETE")
DEFAULT_COVERAGE_STATE: str = "UNCOVERED"


class ClinicalProjectionCoverage(Base):
    """
    Tenant-owned Clinical Projection Coverage persistence at patient/domain grain.
    Initial domains: teeth, treatments, sessions.
    States: UNCOVERED, PARTIAL, COMPLETE.
    Default must never imply COMPLETE (server_default is UNCOVERED).
    Enforces natural uniqueness for tenant+patient+domain, tenant ownership,
    patient relationship, and PostgreSQL RLS.
    """
    __tablename__ = "clinical_projection_coverages"

    __rls_policies__ = _tenant_rls_policy()

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    domain = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default=DEFAULT_COVERAGE_STATE, server_default=DEFAULT_COVERAGE_STATE)
    notes = Column(Text, nullable=True)
    version_id = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "domain IN ('teeth', 'treatments', 'sessions')",
            name="ck_cpc_domain",
        ),
        CheckConstraint(
            "status IN ('UNCOVERED', 'PARTIAL', 'COMPLETE')",
            name="ck_cpc_status",
        ),
        UniqueConstraint("tenant_id", "patient_id", "domain", name="uq_cpc_tenant_patient_domain"),
        Index("ix_cpc_tenant_patient", "tenant_id", "patient_id"),
        Index("ix_cpc_tenant_domain", "tenant_id", "domain"),
    )

    __mapper_args__ = {
        "version_id_col": version_id,
    }

    patient = relationship("Patient")


__all__ = [
    "ClinicalWorkItem",
    "ClinicalWorkItemTarget",
    "ClinicalTreatmentPlan",
    "ClinicalTreatmentPlanPhase",
    "ClinicalTreatmentPlanItem",
    "ClinicalEvent",
    "ClinicalEventTarget",
    "CareSession",
    "CareSessionStep",
    "CareObservation",
    "WorkflowTemplate",
    "NextVisitRequest",
    "ClinicalAttachmentLink",
    "ClinicalProjectionCoverage",
    "COVERAGE_DOMAINS",
    "COVERAGE_STATES",
    "DEFAULT_COVERAGE_STATE",
    "FDI_TOOTH_KEYS",
    "SURFACE_CODES",
    "ROOT_IDS",
    "TARGET_KINDS",
]
