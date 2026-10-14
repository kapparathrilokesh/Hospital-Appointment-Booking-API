
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
import uuid
from app.database import get_db
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.doctor_leave import DoctorLeave
from app.models.doctor_schedule import DoctorSchedule
from app.models.patient import Patient
from app.models.user import User
from app.services.websocket_manager import manager
from app.services.notification_service import send_appointment_confirmation
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentStatusUpdate,
    AppointmentReschedule,
)
from app.routers.auth import get_current_user


router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post(
    "/",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def book_appointment(
    appointment_data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only patients can book appointments.
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can book appointments",
        )

    # Find patient profile.
    patient = db.query(Patient).filter(
        Patient.user_id == current_user.id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Create your patient profile before booking",
        )

    # Find available doctor.
    doctor = db.query(Doctor).filter(
        Doctor.id == appointment_data.doctor_id,
        Doctor.is_available.is_(True),
    ).first()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found or unavailable",
        )

    appointment_time = appointment_data.appointment_datetime

    # Appointment must be in the future.
    if appointment_time <= datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment must be in the future",
        )

    # Check active doctor leave.
    doctor_leave = db.query(DoctorLeave).filter(
        DoctorLeave.doctor_id == doctor.id,
        DoctorLeave.leave_date == appointment_time.date(),
        DoctorLeave.is_active.is_(True),
    ).first()

    if doctor_leave:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Doctor is on leave on the selected date",
        )

    # Find active schedule for the appointment weekday.
    # Monday = 0, Sunday = 6.
    schedule = db.query(DoctorSchedule).filter(
        DoctorSchedule.doctor_id == doctor.id,
        DoctorSchedule.day_of_week == appointment_time.weekday(),
        DoctorSchedule.is_active.is_(True),
    ).first()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Doctor has no active schedule for this weekday",
        )

    appointment_clock = appointment_time.time().replace(tzinfo=None)

    # Check working hours.
    if (
        appointment_clock < schedule.start_time
        or appointment_clock >= schedule.end_time
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment time is outside the doctor's working hours",
        )

    slot_minutes = schedule.slot_duration_minutes

    if slot_minutes <= 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Doctor schedule has an invalid slot duration",
        )

    # Check that the appointment starts on a valid slot boundary.
    schedule_start = datetime.combine(
        appointment_time.date(),
        schedule.start_time,
    )

    elapsed_seconds = (
        appointment_time - schedule_start
    ).total_seconds()

    slot_seconds = slot_minutes * 60

    if elapsed_seconds % slot_seconds != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Appointment must start on a "
                f"{slot_minutes}-minute slot boundary"
            ),
        )

    # Check that the full slot fits within working hours.
    appointment_end = appointment_time + timedelta(
        minutes=slot_minutes
    )

    working_end = datetime.combine(
        appointment_time.date(),
        schedule.end_time,
    )

    if appointment_end > working_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment slot extends beyond working hours",
        )

    # Find existing appointments that start before this slot ends.
    # Check their end times in Python to avoid SQL datetime arithmetic.
    existing_appointments = db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.status.in_(["scheduled", "confirmed"]),
        Appointment.appointment_datetime < appointment_end,
    ).all()

    for existing in existing_appointments:
        existing_end = existing.appointment_datetime + timedelta(
            minutes=slot_minutes
        )

        if existing_end > appointment_time:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This doctor already has an appointment "
                    "during the selected slot"
                ),
            )

   
    # Generate a unique booking reference.
    appointment_number = f"APT-{uuid.uuid4().hex[:12].upper()}"

    # Assign the next queue token for this doctor on this date.
    last_token = (
        db.query(Appointment.token_number)
        .filter(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_datetime >= datetime.combine(
                appointment_time.date(), datetime.min.time()
            ),
            Appointment.appointment_datetime < datetime.combine(
                appointment_time.date() + timedelta(days=1),
                datetime.min.time(),
            ),
        )
        .order_by(Appointment.token_number.desc())
        .first()
    )

    token_number = (last_token[0] or 0) + 1 if last_token else 1

    # Create appointment after validation.
    appointment = Appointment(
        appointment_number=appointment_number,
        token_number=token_number,
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_datetime=appointment_time,
        reason=appointment_data.reason,
        status="scheduled",
        consultation_fee=doctor.consultation_fee,
        reschedule_count=0,
        reminder_sent=False,
    )

    db.add(appointment)
    db.commit()
    db.refresh(appointment)


    # Send appointment confirmation email.
    try:
        send_appointment_confirmation(db, appointment)
    except Exception as exc:
        # Email failure should not undo a successful booking.
        print(f"Appointment confirmation email failed: {exc}")

    return appointment



@router.get(
    "/my",
    response_model=list[AppointmentResponse],
)
def get_my_appointments(
    status_filter: str | None = Query(
        default=None,
        pattern="^(scheduled|confirmed|completed|cancelled)$",
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can view their appointment history",
        )

    patient = db.query(Patient).filter(
        Patient.user_id == current_user.id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found",
        )

    query = db.query(Appointment).filter(
        Appointment.patient_id == patient.id
    )

    if status_filter:
        query = query.filter(
            Appointment.status == status_filter
        )

    return query.order_by(
        Appointment.appointment_datetime.desc()
    ).offset(skip).limit(limit).all()


@router.patch(
    "/{appointment_id}/cancel",
    response_model=AppointmentResponse,
)
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can cancel appointments",
        )

    patient = db.query(Patient).filter(
        Patient.user_id == current_user.id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found",
        )

    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.patient_id == patient.id,
    ).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    if appointment.status in ["cancelled", "completed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This appointment cannot be cancelled",
        )

    appointment.status = "cancelled"

    db.commit()
    db.refresh(appointment)

    return appointment


@router.get(
    "/doctor/my",
    response_model=list[AppointmentResponse],
)
def get_doctor_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can view their appointments",
        )

    doctor = db.query(Doctor).filter(
        Doctor.user_id == current_user.id
    ).first()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found",
        )

    return db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id
    ).order_by(
        Appointment.appointment_datetime.asc()
    ).all()


@router.patch(
    "/{appointment_id}/status",
    response_model=AppointmentResponse,
)
async def update_appointment_status(
    appointment_id: int,
    status_data: AppointmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ["doctor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors or admins can update appointment status",
        )

    appointment = (
        db.query(Appointment)
        .filter(Appointment.id == appointment_id)
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    if current_user.role == "doctor":
        doctor = (
            db.query(Doctor)
            .filter(Doctor.user_id == current_user.id)
            .first()
        )

        if not doctor or appointment.doctor_id != doctor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own appointments",
            )

    appointment.status = status_data.status

    if status_data.notes is not None:
        appointment.notes = status_data.notes

    db.commit()
    db.refresh(appointment)

    await manager.broadcast_to_doctor(
        appointment.doctor_id,
        {
            "event": "appointment_status_updated",
            "appointment_id": appointment.id,
            "doctor_id": appointment.doctor_id,
            "status": appointment.status,
        },
    )

    return appointment


@router.patch(
    "/{appointment_id}/reschedule",
    response_model=AppointmentResponse,
)
def reschedule_appointment(
    appointment_id: int,
    reschedule_data: AppointmentReschedule,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only patients can reschedule their appointments.
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can reschedule appointments",
        )

    patient = db.query(Patient).filter(
        Patient.user_id == current_user.id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found",
        )

    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.patient_id == patient.id,
    ).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    if appointment.status in ["cancelled", "completed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This appointment cannot be rescheduled",
        )

    new_time = reschedule_data.appointment_datetime

    if new_time <= datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New appointment time must be in the future",
        )

    doctor = db.query(Doctor).filter(
        Doctor.id == appointment.doctor_id,
        Doctor.is_available.is_(True),
    ).first()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found or unavailable",
        )

    # Reject dates when the doctor is on leave.
    leave = db.query(DoctorLeave).filter(
        DoctorLeave.doctor_id == doctor.id,
        DoctorLeave.leave_date == new_time.date(),
        DoctorLeave.is_active.is_(True),
    ).first()

    if leave:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Doctor is on leave on the selected date",
        )

    # Find the doctor's active schedule for the new weekday.
    schedule = db.query(DoctorSchedule).filter(
        DoctorSchedule.doctor_id == doctor.id,
        DoctorSchedule.day_of_week == new_time.weekday(),
        DoctorSchedule.is_active.is_(True),
    ).first()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Doctor has no active schedule for this weekday",
        )

    new_clock = new_time.time().replace(tzinfo=None)

    if (
        new_clock < schedule.start_time
        or new_clock >= schedule.end_time
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment time is outside the doctor's working hours",
        )

    slot_minutes = schedule.slot_duration_minutes

    if slot_minutes <= 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Doctor schedule has an invalid slot duration",
        )

    schedule_start = datetime.combine(
        new_time.date(),
        schedule.start_time,
    )

    elapsed_seconds = (new_time - schedule_start).total_seconds()
    slot_seconds = slot_minutes * 60

    if elapsed_seconds % slot_seconds != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Appointment must start on a "
                f"{slot_minutes}-minute slot boundary"
            ),
        )

    new_end = new_time + timedelta(minutes=slot_minutes)
    working_end = datetime.combine(
        new_time.date(),
        schedule.end_time,
    )

    if new_end > working_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment slot extends beyond working hours",
        )

    # Check other active appointments, excluding this appointment.
    existing_appointments = db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.id != appointment.id,
        Appointment.status.in_(["scheduled", "confirmed"]),
        Appointment.appointment_datetime < new_end,
    ).all()

    for existing in existing_appointments:
        existing_end = existing.appointment_datetime + timedelta(
            minutes=slot_minutes
        )

        if existing_end > new_time:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This doctor already has an appointment "
                    "during the selected slot"
                ),
            )

    # Update only after every validation passes.
    appointment.appointment_datetime = new_time
    appointment.status = "scheduled"

    db.commit()
    db.refresh(appointment)

    return appointment
