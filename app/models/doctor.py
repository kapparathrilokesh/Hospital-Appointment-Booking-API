
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), unique=True, nullable=False
    )
    department_id = Column(
        Integer, ForeignKey("departments.id"), nullable=False, index=True
    )
    specialization = Column(String(100), nullable=False)
    qualification = Column(String(150), nullable=False)
    experience_years = Column(Integer, default=0, nullable=False)
    consultation_fee = Column(Integer, nullable=False, default=0)
    bio = Column(Text, nullable=True)
    is_available = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User")
    department = relationship("Department")
