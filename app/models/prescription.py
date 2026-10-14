
from sqlalchemy import (
    Column,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)

    consultation_id = Column(
        Integer,
        ForeignKey("consultations.id"),
        nullable=False,
        index=True,
    )

    medication_name = Column(Text, nullable=False)
    dosage = Column(Text, nullable=False)
    frequency = Column(Text, nullable=False)
    duration = Column(Text, nullable=False)
    instructions = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    consultation = relationship("Consultation")
