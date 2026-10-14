
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.doctor import Doctor
from app.models.doctor_leave import DoctorLeave
from app.schemas.doctor_leave import (
    DoctorLeaveCreate,
    DoctorLeaveResponse,
)
from app.routers.auth import get_current_user, require_roles


router = APIRouter(
    prefix="/doctor-leaves",
    tags=["Doctor Leaves"],
)


@router.post(
    "/",
    response_model=DoctorLeaveResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_doctor_leave(
    leave_data: DoctorLeaveCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    doctor = db.query(Doctor).filter(
        Doctor.id == leave_data.doctor_id
    ).first()

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found",
        )

    existing_leave = db.query(DoctorLeave).filter(
        DoctorLeave.doctor_id == leave_data.doctor_id,
        DoctorLeave.leave_date == leave_data.leave_date,
        DoctorLeave.is_active.is_(True),
    ).first()

    if existing_leave:
        raise HTTPException(
            status_code=409,
            detail="Active leave already exists for this doctor on that date",
        )

    leave = DoctorLeave(**leave_data.model_dump())
    db.add(leave)
    db.commit()
    db.refresh(leave)

    return leave


@router.get(
    "/",
    response_model=list[DoctorLeaveResponse],
)
def list_doctor_leaves(
    doctor_id: int | None = None,
    leave_date: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(DoctorLeave).filter(
        DoctorLeave.is_active.is_(True)
    )

    if doctor_id is not None:
        query = query.filter(
            DoctorLeave.doctor_id == doctor_id
        )

    if leave_date is not None:
        query = query.filter(
            DoctorLeave.leave_date == leave_date
        )

    return query.order_by(
        DoctorLeave.leave_date
    ).all()


@router.delete(
    "/{leave_id}",
    response_model=DoctorLeaveResponse,
)
def cancel_doctor_leave(
    leave_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    leave = db.query(DoctorLeave).filter(
        DoctorLeave.id == leave_id,
        DoctorLeave.is_active.is_(True),
    ).first()

    if not leave:
        raise HTTPException(
            status_code=404,
            detail="Active doctor leave not found",
        )

    leave.is_active = False
    db.commit()
    db.refresh(leave)

    return leave
