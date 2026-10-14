
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AppointmentCreate(BaseModel):
    doctor_id: int = Field(gt=0)
    appointment_datetime: datetime
    reason: Optional[str] = None


class AppointmentStatusUpdate(BaseModel):
    status: str = Field(
        pattern="^(scheduled|confirmed|checked-in|in consultation|completed|cancelled|no-show)$"
    )
    notes: Optional[str] = None


class AppointmentResponse(BaseModel):
    id: int
    appointment_number: Optional[str] = None
    token_number: Optional[int] = None
    patient_id: int
    doctor_id: int
    appointment_datetime: datetime
    reason: Optional[str] = None
    status: str
    notes: Optional[str] = None
    consultation_fee: int
    reschedule_count: int
    reminder_sent: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AppointmentReschedule(BaseModel):
    appointment_datetime: datetime
