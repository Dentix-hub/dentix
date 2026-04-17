"""Patient-related schemas."""

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


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

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "phone": "+201098765432",
                    "notes": "Updated contact info",
                }
            ]
        }
    )


class Patient(PatientBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PatientSummary(BaseModel):
    id: int
    name: str
    age: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AttachmentBase(BaseModel):
    patient_id: int
    filename: str
    file_type: str


class AttachmentCreate(AttachmentBase):
    file_path: str


class Attachment(AttachmentBase):
    id: int
    created_at: datetime
    file_path: str

    model_config = ConfigDict(from_attributes=True)
