
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PrescriptionCreate(BaseModel):
    consultation_id: int = Field(gt=0)
    medication_name: str = Field(min_length=1, max_length=500)
    dosage: str = Field(min_length=1, max_length=500)
    frequency: str = Field(min_length=1, max_length=500)
    duration: str = Field(min_length=1, max_length=500)
    instructions: Optional[str] = None


class PrescriptionResponse(BaseModel):
    id: int
    consultation_id: int
    medication_name: str
    dosage: str
    frequency: str
    duration: str
    instructions: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
