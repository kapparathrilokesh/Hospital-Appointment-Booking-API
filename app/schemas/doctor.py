
from pydantic import BaseModel, ConfigDict, Field


class DoctorCreate(BaseModel):
    user_id: int = Field(gt=0)
    department_id: int = Field(gt=0)
    specialization: str = Field(min_length=2, max_length=100)
    qualification: str = Field(min_length=2, max_length=150)
    experience_years: int = Field(default=0, ge=0, le=70)
    consultation_fee: int = Field(ge=0)
    bio: str | None = Field(default=None, max_length=2000)


class DoctorUpdate(BaseModel):
    department_id: int | None = Field(default=None, gt=0)
    specialization: str | None = Field(default=None, min_length=2, max_length=100)
    qualification: str | None = Field(default=None, min_length=2, max_length=150)
    experience_years: int | None = Field(default=None, ge=0, le=70)
    consultation_fee: int | None = Field(default=None, ge=0)
    bio: str | None = Field(default=None, max_length=2000)
    is_available: bool | None = None


class DoctorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    department_id: int
    specialization: str
    qualification: str
    experience_years: int
    consultation_fee: int
    bio: str | None
    is_available: bool
