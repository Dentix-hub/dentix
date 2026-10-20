from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.clinical.catalog import CANONICAL_ATTACHMENT_PURPOSE_CODES, AttachmentPurposeCode
from backend.models.clinical_core import FDI_TOOTH_KEYS


class ClinicalAttachmentLinkBase(BaseModel):
    attachment_id: int
    work_item_id: Optional[int] = None
    care_session_id: Optional[int] = None
    clinical_event_id: Optional[int] = None
    tooth_key: Optional[str] = None
    purpose_code: str = Field(default=AttachmentPurposeCode.OTHER.value)
    notes: Optional[str] = None

    @field_validator("tooth_key")
    @classmethod
    def validate_tooth_key(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in FDI_TOOTH_KEYS:
            raise ValueError(f"Tooth key '{v}' is not a valid FDI tooth notation (11-48, 51-85)")
        return v

    @field_validator("purpose_code")
    @classmethod
    def validate_purpose_code(cls, v: str) -> str:
        if v not in CANONICAL_ATTACHMENT_PURPOSE_CODES:
            raise ValueError(
                f"Purpose code '{v}' is not allowed. Must be one of: {', '.join(CANONICAL_ATTACHMENT_PURPOSE_CODES)}"
            )
        return v

    @model_validator(mode="after")
    def validate_context_present(self) -> "ClinicalAttachmentLinkBase":
        if (
            self.work_item_id is None
            and self.care_session_id is None
            and self.clinical_event_id is None
            and self.tooth_key is None
        ):
            raise ValueError(
                "At least one clinical context (work_item_id, care_session_id, clinical_event_id, or tooth_key) must be provided"
            )
        return self


class ClinicalAttachmentLinkCreate(ClinicalAttachmentLinkBase):
    pass


class ClinicalAttachmentLinkRead(BaseModel):
    id: int
    tenant_id: int
    patient_id: int
    attachment_id: int
    work_item_id: Optional[int] = None
    care_session_id: Optional[int] = None
    clinical_event_id: Optional[int] = None
    tooth_key: Optional[str] = None
    purpose_code: str
    notes: Optional[str] = None
    created_at: datetime

    # Denormalized file information for easy frontend/inspector consumption
    filename: Optional[str] = None
    file_path: Optional[str] = None
    file_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ClinicalAttachmentLinkFilter(BaseModel):
    attachment_id: Optional[int] = None
    work_item_id: Optional[int] = None
    care_session_id: Optional[int] = None
    clinical_event_id: Optional[int] = None
    tooth_key: Optional[str] = None
    purpose_code: Optional[str] = None
