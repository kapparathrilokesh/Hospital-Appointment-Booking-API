
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Consultation(Base):
    __tablename__ = "consultations"
    __table_args__ = (
        UniqueConstraint(
            "appointment_id",
            name="uq_consultation_appointment",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    appointment_id = Column(
        Integer,
        ForeignKey("appointments.id"),
        nullable=False,
        index=True,
    )

    diagnosis = Column(Text, nullable=False)
    treatment_plan = Column(Text, nullable=True)
    follow_up_date = Column(Date, nullable=True)

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    appointment = relationship("Appointment")
