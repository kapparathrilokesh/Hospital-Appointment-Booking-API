
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.doctor import Doctor
from app.models.doctor_schedule import DoctorSchedule
from app.schemas.doctor_schedule import (
    DoctorScheduleCreate,
    DoctorScheduleUpdate,
    DoctorScheduleResponse,
)
from app.routers.auth import get_current_user, require_roles


router = APIRouter(
    prefix="/doctor-schedules",
    tags=["Doctor Schedules"],
)


@router.post(
    "/",
    response_model=DoctorScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_doctor_schedule(
    schedule_data: DoctorScheduleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    doctor = db.query(Doctor).filter(
        Doctor.id == schedule_data.doctor_id,
        Doctor.is_available.is_(True),
    ).first()

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Available doctor not found",
        )

    existing_schedule = db.query(DoctorSchedule).filter(
        DoctorSchedule.doctor_id == schedule_data.doctor_id,
        DoctorSchedule.day_of_week == schedule_data.day_of_week,
    ).first()

    if existing_schedule:
        raise HTTPException(
            status_code=409,
            detail="A schedule already exists for this doctor on that day",
        )

    schedule = DoctorSchedule(**schedule_data.model_dump())
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    return schedule


@router.get(
    "/",
    response_model=list[DoctorScheduleResponse],
)
def list_doctor_schedules(
    doctor_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(DoctorSchedule)

    if doctor_id is not None:
        query = query.filter(
            DoctorSchedule.doctor_id == doctor_id
        )

    return query.order_by(
        DoctorSchedule.doctor_id,
        DoctorSchedule.day_of_week,
    ).all()


@router.get(
    "/{schedule_id}",
    response_model=DoctorScheduleResponse,
)
def get_doctor_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    schedule = db.query(DoctorSchedule).filter(
        DoctorSchedule.id == schedule_id
    ).first()

    if not schedule:
        raise HTTPException(
            status_code=404,
            detail="Doctor schedule not found",
        )

    return schedule


@router.patch(
    "/{schedule_id}",
    response_model=DoctorScheduleResponse,
)
def update_doctor_schedule(
    schedule_id: int,
    schedule_data: DoctorScheduleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    schedule = db.query(DoctorSchedule).filter(
        DoctorSchedule.id == schedule_id
    ).first()

    if not schedule:
        raise HTTPException(
            status_code=404,
            detail="Doctor schedule not found",
        )

    updates = schedule_data.model_dump(exclude_unset=True)

    new_day = updates.get("day_of_week", schedule.day_of_week)
    new_start = updates.get("start_time", schedule.start_time)
    new_end = updates.get("end_time", schedule.end_time)

    if new_start is not None and new_end is not None:
        if new_start >= new_end:
            raise HTTPException(
                status_code=422,
                detail="start_time must be earlier than end_time",
            )

    if new_day != schedule.day_of_week:
        duplicate = db.query(DoctorSchedule).filter(
            DoctorSchedule.doctor_id == schedule.doctor_id,
            DoctorSchedule.day_of_week == new_day,
            DoctorSchedule.id != schedule.id,
        ).first()

        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="A schedule already exists for this doctor on that day",
            )

    for field, value in updates.items():
        setattr(schedule, field, value)

    db.commit()
    db.refresh(schedule)

    return schedule


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_200_OK,
)
def deactivate_doctor_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    schedule = db.query(DoctorSchedule).filter(
        DoctorSchedule.id == schedule_id
    ).first()

    if not schedule:
        raise HTTPException(
            status_code=404,
            detail="Doctor schedule not found",
        )

    schedule.is_active = False
    db.commit()

    return {
        "message": "Doctor schedule deactivated successfully"
    }
