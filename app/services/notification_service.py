
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.user import User
from app.services.email_service import send_email


def send_appointment_confirmation(db, appointment: Appointment) -> bool:
    """Email the patient after an appointment is successfully booked."""

    patient = (
        db.query(Patient)
        .filter(Patient.id == appointment.patient_id)
        .first()
    )

    if not patient:
        return False

    user = (
        db.query(User)
        .filter(User.id == patient.user_id)
        .first()
    )

    if not user or not user.email:
        return False

    subject = "Hospital Appointment Confirmation"
    body = (
        f"Hello {user.full_name},\n\n"
        "Your hospital appointment has been booked successfully.\n\n"
        f"Appointment ID: {appointment.id}\n"
        f"Date and time: {appointment.appointment_datetime}\n"
        f"Status: {appointment.status}\n\n"
        "Please contact the hospital if you need to change your appointment.\n\n"
        "Thank you."
    )

    return send_email(user.email, subject, body)
