"""
Workflow Template Schemas (Care Sessions VNext).
Provides data validation and serialization for clinic-owned workflow templates,
ordered steps, configurable custom fields, and template snapshots.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


VALID_FIELD_TYPES = {"text", "multiline", "number", "date", "boolean", "choice"}
SLUG_REGEX = re.compile(r"^[a-z0-9_]{1,64}$")
HTML_TAG_REGEX = re.compile(r"<[^>]+>")


def sanitize_no_scripts(v: str) -> str:
    """Disallow script tags or executable code in template definitions."""
    if not isinstance(v, str):
        return v
    if "<script" in v.lower() or "javascript:" in v.lower() or "onload=" in v.lower() or "onerror=" in v.lower():
        raise ValueError("Template definition contains disallowed script or executable content")
    return v.strip()


class WorkflowFieldSchema(BaseModel):
    field_id: str = Field(..., description="Stable field identifier (slug format)")
    field_type: str = Field(..., description="Field type: text, multiline, number, date, boolean, choice")
    label: str = Field(..., description="Human-readable field label")
    description: Optional[str] = Field(None, description="Optional field instructions or helper text")
    is_required: bool = Field(False, description="Whether this field must be completed before session finalization")
    unit: Optional[str] = Field(None, description="Optional unit label (e.g. mm, Ncm, min)")
    choices: Optional[List[str]] = Field(default_factory=list, description="Available options when field_type is choice")
    default_value: Optional[Any] = Field(None, description="Optional default value")

    @field_validator("field_id")
    @classmethod
    def validate_field_id(cls, v: str) -> str:
        s = v.strip().lower()
        if not SLUG_REGEX.match(s):
            raise ValueError(f"field_id '{v}' must be 1-64 lowercase alphanumeric/underscore characters")
        return s

    @field_validator("field_type")
    @classmethod
    def validate_field_type(cls, v: str) -> str:
        s = v.strip().lower()
        if s not in VALID_FIELD_TYPES:
            raise ValueError(f"field_type '{v}' is not supported. Allowed: {sorted(VALID_FIELD_TYPES)}")
        return s

    @field_validator("label")
    @classmethod
    def validate_label(cls, v: str) -> str:
        cleaned = sanitize_no_scripts(v)
        if not cleaned:
            raise ValueError("Field label cannot be empty")
        return cleaned

    @field_validator("description", "unit")
    @classmethod
    def sanitize_text_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return sanitize_no_scripts(v)

    @field_validator("choices")
    @classmethod
    def sanitize_choices(cls, v: Optional[List[str]]) -> List[str]:
        if not v:
            return []
        cleaned = []
        seen = set()
        for c in v:
            c_clean = sanitize_no_scripts(str(c))
            if not c_clean:
                continue
            if c_clean in seen:
                continue
            seen.add(c_clean)
            cleaned.append(c_clean)
        return cleaned

    @model_validator(mode="after")
    def validate_choice_has_options(self) -> WorkflowFieldSchema:
        if self.field_type == "choice":
            if not self.choices or len(self.choices) < 1:
                raise ValueError(f"Field '{self.field_id}' of type 'choice' must have at least one non-empty choice option")
        return self


class WorkflowStepSchema(BaseModel):
    step_code: str = Field(..., description="Stable step code")
    step_order: int = Field(..., ge=1, description="Sequential 1-based order")
    title: str = Field(..., description="Step title")
    description: Optional[str] = Field(None, description="Step description")
    is_required: bool = Field(False, description="Whether step is mandatory")
    repeatable: bool = Field(False, description="Whether step can be performed repeatedly")

    @field_validator("step_code")
    @classmethod
    def validate_step_code(cls, v: str) -> str:
        s = v.strip().lower()
        if not SLUG_REGEX.match(s):
            raise ValueError(f"step_code '{v}' must be 1-64 lowercase alphanumeric/underscore characters")
        return s

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        cleaned = sanitize_no_scripts(v)
        if not cleaned:
            raise ValueError("Step title cannot be empty")
        return cleaned

    @field_validator("description")
    @classmethod
    def sanitize_desc(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return sanitize_no_scripts(v)


class WorkflowTemplateDefinitionPayload(BaseModel):
    steps: List[WorkflowStepSchema] = Field(default_factory=list, description="Ordered workflow steps")
    custom_fields: List[WorkflowFieldSchema] = Field(default_factory=list, description="Configurable custom fields")

    @model_validator(mode="after")
    def validate_steps_and_fields(self) -> WorkflowTemplateDefinitionPayload:
        if not self.steps:
            raise ValueError("Template must contain at least one step")

        # Validate step order sequentiality and code uniqueness
        seen_codes = set()
        seen_orders = set()
        sorted_steps = sorted(self.steps, key=lambda s: s.step_order)
        for idx, step in enumerate(sorted_steps):
            if step.step_code in seen_codes:
                raise ValueError(f"Duplicate step_code '{step.step_code}' in template steps")
            seen_codes.add(step.step_code)

            if step.step_order in seen_orders:
                raise ValueError(f"Duplicate step_order {step.step_order} in template steps")
            seen_orders.add(step.step_order)

            expected_order = idx + 1
            if step.step_order != expected_order:
                raise ValueError(f"Step ordering must be sequential 1..N. Got {step.step_order}, expected {expected_order}")

        # Validate custom fields identifier uniqueness
        seen_fields = set()
        for field in self.custom_fields:
            if field.field_id in seen_fields:
                raise ValueError(f"Duplicate field_id '{field.field_id}' in template custom fields")
            seen_fields.add(field.field_id)

        return self


class WorkflowTemplateCreate(BaseModel):
    template_code: str = Field(..., description="Unique template identifier (e.g. ENDO_RCT, PROS_CROWN)")
    title: str = Field(..., description="Display title of the template")
    procedure_code: Optional[str] = Field(None, description="Canonical procedure code association")
    description: Optional[str] = Field(None, description="Template documentation description")
    definition: WorkflowTemplateDefinitionPayload = Field(..., description="Steps and custom fields")
    is_active: bool = Field(True, description="Whether template is active for new visits")

    @field_validator("template_code")
    @classmethod
    def validate_template_code(cls, v: str) -> str:
        s = v.strip().upper()
        if not re.match(r"^[A-Z0-9_]{1,64}$", s):
            raise ValueError(f"template_code '{v}' must be 1-64 uppercase alphanumeric/underscore characters")
        return s

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        cleaned = sanitize_no_scripts(v)
        if not cleaned:
            raise ValueError("Template title cannot be empty")
        return cleaned


class WorkflowTemplateUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Updated display title")
    procedure_code: Optional[str] = Field(None, description="Procedure code association")
    description: Optional[str] = Field(None, description="Updated description")
    definition: Optional[WorkflowTemplateDefinitionPayload] = Field(None, description="Updated steps and fields")
    is_active: Optional[bool] = Field(None, description="Active status")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = sanitize_no_scripts(v)
        if not cleaned:
            raise ValueError("Template title cannot be empty")
        return cleaned


class WorkflowTemplateRead(BaseModel):
    id: int
    tenant_id: int
    template_code: str
    version: int
    title: str
    procedure_code: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    definition: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
