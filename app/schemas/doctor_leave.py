
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class DoctorLeaveCreate(BaseModel):
    doctor_id: int = Field(gt=0)
    leave_date: date
    reason: str | None = Field(default=None, max_length=255)


class DoctorLeaveResponse(BaseModel):
    id: int
    doctor_id: int
    leave_date: date
    reason: str | None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
