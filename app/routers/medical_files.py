
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.medical_file import MedicalFile
from app.models.patient import Patient
from app.models.user import User
from app.schemas.medical_file import MedicalFileResponse
from app.routers.auth import get_current_user


router = APIRouter(prefix="/medical-files", tags=["Medical Files"])

UPLOAD_DIR = Path("uploads/medical")
ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload", response_model=MedicalFileResponse, status_code=201)
async def upload_medical_file(
    patient_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Patients can upload only to their own record.
    # Doctors can upload only for patients they have an appointment with.
    if current_user.role == "patient":
        if patient.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not your patient record")
    elif current_user.role == "doctor":
        from app.models.appointment import Appointment
        from app.models.doctor import Doctor

        doctor = db.query(Doctor).filter(
            Doctor.user_id == current_user.id
        ).first()
        if not doctor:
            raise HTTPException(status_code=403, detail="Doctor profile not found")

        has_appointment = db.query(Appointment).filter(
            Appointment.doctor_id == doctor.id,
            Appointment.patient_id == patient.id,
        ).first()
        if not has_appointment:
            raise HTTPException(
                status_code=403,
                detail="You can upload files only for your patients",
            )
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    extension = ALLOWED_TYPES.get(file.content_type)
    if not extension:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, JPG, and PNG files are allowed",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid.uuid4().hex}{extension}"
    destination = UPLOAD_DIR / stored_filename
    size = 0

    try:
        with destination.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="File exceeds the 10 MB limit",
                    )
                output.write(chunk)

        record = MedicalFile(
            patient_id=patient.id,
            uploaded_by=current_user.id,
            original_filename=Path(file.filename or "upload").name[:255],
            stored_filename=stored_filename,
            file_path=str(destination),
            content_type=file.content_type,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    except Exception:
        if destination.exists():
            destination.unlink()
        raise
    finally:
        await file.close()


@router.get("/patient/{patient_id}", response_model=list[MedicalFileResponse])
def list_patient_files(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if current_user.role == "patient":
        if patient.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not your patient record")
    elif current_user.role == "doctor":
        from app.models.appointment import Appointment
        from app.models.doctor import Doctor

        doctor = db.query(Doctor).filter(
            Doctor.user_id == current_user.id
        ).first()
        has_appointment = doctor and db.query(Appointment).filter(
            Appointment.doctor_id == doctor.id,
            Appointment.patient_id == patient.id,
        ).first()
        if not has_appointment:
            raise HTTPException(status_code=403, detail="Not authorized")
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    return (
        db.query(MedicalFile)
        .filter(MedicalFile.patient_id == patient_id)
        .order_by(MedicalFile.created_at.desc())
        .all()
    )
