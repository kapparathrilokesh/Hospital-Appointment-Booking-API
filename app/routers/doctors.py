
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.user import User
from app.routers.auth import get_current_user, require_roles
from app.schemas.doctor import DoctorCreate, DoctorResponse, DoctorUpdate

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.post(
    "/",
    response_model=DoctorResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_doctor(
    data: DoctorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user or user.role != "doctor" or not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="An active user with the doctor role is required",
        )

    department = db.query(Department).filter(
        Department.id == data.department_id,
        Department.is_active.is_(True),
    ).first()
    if not department:
        raise HTTPException(
            status_code=404,
            detail="Active department not found",
        )

    doctor = Doctor(**data.model_dump())
    try:
        db.add(doctor)
        db.commit()
        db.refresh(doctor)
        return doctor
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This user may already have a doctor profile",
        )


@router.get("/", response_model=list[DoctorResponse])
def list_doctors(
    department_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Doctor).join(User).filter(
        Doctor.is_available.is_(True),
        User.is_active.is_(True),
    )

    if department_id is not None:
        query = query.filter(Doctor.department_id == department_id)

    return query.order_by(Doctor.id).all()


@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doctor = (
        db.query(Doctor)
        .join(User)
        .filter(
            Doctor.id == doctor_id,
            Doctor.is_available.is_(True),
            User.is_active.is_(True),
        )
        .first()
    )
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor


@router.patch("/{doctor_id}", response_model=DoctorResponse)
def update_doctor(
    doctor_id: int,
    data: DoctorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    changes = data.model_dump(exclude_unset=True)

    if "department_id" in changes and changes["department_id"] is not None:
        department = db.query(Department).filter(
            Department.id == changes["department_id"],
            Department.is_active.is_(True),
        ).first()
        if not department:
            raise HTTPException(status_code=404, detail="Active department not found")

    for field, value in changes.items():
        setattr(doctor, field, value)

    try:
        db.commit()
        db.refresh(doctor)
        return doctor
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Could not update doctor")


@router.delete("/{doctor_id}", status_code=status.HTTP_200_OK)
def deactivate_doctor(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    doctor.is_available = False
    db.commit()
    return {"message": "Doctor marked as unavailable"}
