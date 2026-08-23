"""Finance V2 request/metadata schemas.

Keep write semantics explicit: compensation settings are partial updates and an
omitted field must never be interpreted as zero.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, model_validator

from backend.core.money import NonNegativeMoney, Percentage


class CompensationSettingsPatch(BaseModel):
    """Atomic partial update for compensation configuration.

    ``None`` is not a supported business value for these persisted fields.  A
    client must omit fields it does not intend to change.
    """

    commission_percent: Optional[Percentage] = None
    fixed_salary: Optional[NonNegativeMoney] = None
    per_appointment_fee: Optional[NonNegativeMoney] = None
    hire_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_partial_update(self):
        if not self.model_fields_set:
            raise ValueError("At least one compensation field is required")
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null; omit it to preserve the current value")
        return self


class FinancePeriodMetadata(BaseModel):
    kind: str = "period"
    scope: str = "period"
    start: str
    end: str
    timezone: str


class FinanceMetricDefinition(BaseModel):
    scope: str
    formula: str
    description: str
