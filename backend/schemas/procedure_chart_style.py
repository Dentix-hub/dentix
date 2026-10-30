"""
Pydantic schemas for Procedure Chart Styles (UX Stabilization U4).
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.clinical.chart_styles import (
    CHART_STYLE_COLOR_KEYS,
    CHART_STYLE_TEMPLATES,
)


class ProcedureChartStyleBase(BaseModel):
    procedure_name: str = Field(..., max_length=255)
    template: str = Field(..., max_length=32)
    color_key: Optional[str] = Field(None, max_length=16)

    @field_validator("template")
    @classmethod
    def validate_template(cls, v: str) -> str:
        if v not in CHART_STYLE_TEMPLATES:
            raise ValueError(f"Template '{v}' is not valid. Allowed: {CHART_STYLE_TEMPLATES}")
        return v

    @field_validator("color_key")
    @classmethod
    def validate_color_key(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in CHART_STYLE_COLOR_KEYS:
            raise ValueError(f"Color key '{v}' is not valid. Allowed: {CHART_STYLE_COLOR_KEYS}")
        return v

    @model_validator(mode="after")
    def validate_none_has_no_color(self) -> "ProcedureChartStyleBase":
        if self.template == "NONE" and self.color_key is not None:
            raise ValueError("color_key must be null when template is 'NONE'")
        return self


class ProcedureChartStyleCreate(ProcedureChartStyleBase):
    pass


class ProcedureChartStyleRead(ProcedureChartStyleBase):
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProcedureChartStyleEmbedded(BaseModel):
    template: str
    color_key: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
