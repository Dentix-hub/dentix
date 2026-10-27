"""Patient-related schemas."""

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PatientBase(BaseModel):
    name: str
    gender: Optional[str] = None
    age: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    medical_history: Optional[str] = None
    notes: Optional[str] = None
    assigned_doctor_id: Optional[int] = None
    default_price_list_id: Optional[int] = None
    date_of_birth: Optional[date] = None

    @field_validator("age", "assigned_doctor_id", "default_price_list_id", "date_of_birth", mode="before")
    @classmethod
    def coerce_empty_to_none(cls, v):
        if v == "" or (isinstance(v, str) and not v.strip()):
            return None
        return v


class PatientCreate(PatientBase):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Ahmed Ali",
                    "gender": "male",
                    "age": 35,
                    "phone": "+201012345678",
                    "email": "ahmed@example.com",
                    "address": "Cairo, Egypt",
                    "medical_history": "No known allergies",
                    "notes": "Referred by Dr. Khaled",
                }
            ]
        }
    )


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    medical_history: Optional[str] = None
    notes: Optional[str] = None
    default_price_list_id: Optional[int] = None
    assigned_doctor_id: Optional[int] = None
    date_of_birth: Optional[date] = None

    @field_validator("age", "assigned_doctor_id", "default_price_list_id", "date_of_birth", mode="before")
    @classmethod
    def coerce_empty_to_none(cls, v):
        if v == "" or (isinstance(v, str) and not v.strip()):
            return None
        return v

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"phone": "+201098765432", "notes": "Updated contact info"}]}
    )


class MedicalAlert(BaseModel):
    has_alert: bool = False
    kinds: list[str] = Field(default_factory=list)


class Patient(PatientBase):
    id: int
    created_at: Optional[datetime] = None
    date_of_birth_precision: Optional[str] = None
    age_recorded_at: Optional[datetime] = None
    medical_alert: MedicalAlert = Field(default_factory=MedicalAlert)

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _populate_alert(cls, data: Any) -> Any:
        from backend.utils.medical_alerts import derive_medical_alerts
        if isinstance(data, dict):
            if "medical_alert" not in data or data["medical_alert"] is None:
                history = data.get("medical_history")
                data["medical_alert"] = derive_medical_alerts(history)
        return data


class PatientSummary(BaseModel):
    id: int
    name: str
    age: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    created_at: Optional[datetime] = None
    date_of_birth: Optional[date] = None
    date_of_birth_precision: Optional[str] = None
    age_recorded_at: Optional[datetime] = None
    medical_alert: MedicalAlert = Field(default_factory=MedicalAlert)

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _populate_alert(cls, data: Any) -> Any:
        from backend.utils.medical_alerts import derive_medical_alerts
        if isinstance(data, dict):
            if "medical_alert" not in data or data["medical_alert"] is None:
                history = data.get("medical_history")
                data["medical_alert"] = derive_medical_alerts(history)
        return data


class PatientDirectoryItem(BaseModel):
    id: int
    file_number: int
    name: str
    age: Optional[int] = None
    phone: Optional[str] = None
    assigned_doctor_id: Optional[int] = None
    assigned_doctor_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    date_of_birth_precision: Optional[str] = None
    age_recorded_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    medical_alert: MedicalAlert = Field(default_factory=MedicalAlert)

    model_config = ConfigDict(from_attributes=True)


class AttachmentBase(BaseModel):
    patient_id: int
    filename: str
    file_type: str
    note: Optional[str] = None


class AttachmentCreate(AttachmentBase):
    file_path: str


class Attachment(AttachmentBase):
    id: int
    created_at: datetime
    file_path: str
    storage_status: str = "ready"

    model_config = ConfigDict(from_attributes=True)
