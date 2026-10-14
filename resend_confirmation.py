
from app.database import SessionLocal
from app.models.appointment import Appointment
from app.services.notification_service import send_appointment_confirmation

db = SessionLocal()

try:
    appointment = (
        db.query(Appointment)
        .filter(Appointment.id == 4)
        .first()
    )

    if not appointment:
        print("Appointment ID 4 was not found.")
    else:
        send_appointment_confirmation(db, appointment)
        print("Appointment confirmation email sent successfully!")

except Exception as exc:
    print(f"Email sending failed: {exc}")

finally:
    db.close()
