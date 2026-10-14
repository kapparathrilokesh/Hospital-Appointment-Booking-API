
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.appointment import Appointment
from app.models.consultation import Consultation
from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.consultation import (
    ConsultationCreate,
    ConsultationResponse,
)
from app.routers.auth import get_current_user


router = APIRouter(
    prefix="/consultations",
    tags=["Consultations"],
)


@router.post(
    "/",
    response_model=ConsultationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_consultation(
    consultation_data: ConsultationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["doctor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors or admins can create consultations",
        )

    appointment = db.query(Appointment).filter(
        Appointment.id == consultation_data.appointment_id
    ).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    if appointment.status not in ["confirmed", "completed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consultations require a confirmed or completed appointment",
        )

    if current_user.role == "doctor":
        doctor = db.query(Doctor).filter(
            Doctor.user_id == current_user.id
        ).first()

        if not doctor or appointment.doctor_id != doctor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only manage your own appointments",
            )

    existing = db.query(Consultation).filter(
        Consultation.appointment_id == appointment.id
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A consultation already exists for this appointment",
        )

    consultation = Consultation(
        appointment_id=appointment.id,
        diagnosis=consultation_data.diagnosis,
        treatment_plan=consultation_data.treatment_plan,
        follow_up_date=consultation_data.follow_up_date,
    )

    db.add(consultation)
    db.commit()
    db.refresh(consultation)

    return consultation


@router.get(
    "/{consultation_id}",
    response_model=ConsultationResponse,
)
def get_consultation(
    consultation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    consultation = db.query(Consultation).filter(
        Consultation.id == consultation_id
    ).first()

    if not consultation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consultation not found",
        )

    appointment = db.query(Appointment).filter(
        Appointment.id == consultation.appointment_id
    ).first()

    if current_user.role == "admin":
        return consultation

    if current_user.role == "doctor":
        doctor = db.query(Doctor).filter(
            Doctor.user_id == current_user.id
        ).first()

        if doctor and appointment and appointment.doctor_id == doctor.id:
            return consultation

    # Patients may view only consultations for their own appointments.
    from app.models.patient import Patient

    if current_user.role == "patient":
        patient = db.query(Patient).filter(
            Patient.user_id == current_user.id
        ).first()

        if patient and appointment and appointment.patient_id == patient.id:
            return consultation

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You are not allowed to view this consultation",
    )
