
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class MedicalFileResponse(BaseModel):
    id: int
    patient_id: int
    uploaded_by: int
    original_filename: str
    content_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
