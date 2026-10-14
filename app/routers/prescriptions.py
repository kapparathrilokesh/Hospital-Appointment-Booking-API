
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.appointment import Appointment
from app.models.consultation import Consultation
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.prescription import Prescription
from app.models.user import User
from app.schemas.prescription import (
    PrescriptionCreate,
    PrescriptionResponse,
)
from app.routers.auth import get_current_user


router = APIRouter(
    prefix="/prescriptions",
    tags=["Prescriptions"],
)


def get_authorized_consultation(
    consultation_id: int,
    db: Session,
    current_user: User,
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

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    if current_user.role == "admin":
        return consultation

    if current_user.role == "doctor":
        doctor = db.query(Doctor).filter(
            Doctor.user_id == current_user.id
        ).first()

        if doctor and appointment.doctor_id == doctor.id:
            return consultation

    if current_user.role == "patient":
        patient = db.query(Patient).filter(
            Patient.user_id == current_user.id
        ).first()

        if patient and appointment.patient_id == patient.id:
            return consultation

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You are not allowed to access this consultation",
    )


@router.post(
    "/",
    response_model=PrescriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_prescription(
    prescription_data: PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["doctor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors or admins can create prescriptions",
        )

    get_authorized_consultation(
        prescription_data.consultation_id,
        db,
        current_user,
    )

    prescription = Prescription(
        consultation_id=prescription_data.consultation_id,
        medication_name=prescription_data.medication_name,
        dosage=prescription_data.dosage,
        frequency=prescription_data.frequency,
        duration=prescription_data.duration,
        instructions=prescription_data.instructions,
    )

    db.add(prescription)
    db.commit()
    db.refresh(prescription)

    return prescription


@router.get(
    "/consultation/{consultation_id}",
    response_model=list[PrescriptionResponse],
)
def get_prescriptions_for_consultation(
    consultation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_authorized_consultation(
        consultation_id,
        db,
        current_user,
    )

    return db.query(Prescription).filter(
        Prescription.consultation_id == consultation_id
    ).order_by(Prescription.id.asc()).all()
