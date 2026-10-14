
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConsultationCreate(BaseModel):
    appointment_id: int = Field(gt=0)
    diagnosis: str = Field(min_length=1)
    treatment_plan: Optional[str] = None
    follow_up_date: Optional[date] = None

    @field_validator("diagnosis")
    @classmethod
    def diagnosis_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Diagnosis cannot be blank")
        return value.strip()


class ConsultationResponse(BaseModel):
    id: int
    appointment_id: int
    diagnosis: str
    treatment_plan: Optional[str] = None
    follow_up_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
