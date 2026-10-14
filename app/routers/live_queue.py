
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.user import User
from app.services.websocket_manager import manager
from app.utils.security import decode_token

router = APIRouter(tags=["Live Queue"])


@router.websocket("/ws/queue/{doctor_id}")
async def doctor_live_queue(websocket: WebSocket, doctor_id: int):
    db: Session = SessionLocal()
    connected = False

    try:
        # 1. Authenticate using an access token.
        token = websocket.query_params.get("token")

        if not token:
            await websocket.close(
                code=1008,
                reason="Access token required",
            )
            return

        payload = decode_token(token)

        if not payload or payload.get("type") != "access":
            await websocket.close(
                code=1008,
                reason="Invalid or expired access token",
            )
            return

        try:
            user_id = int(payload["sub"])
        except (KeyError, TypeError, ValueError):
            await websocket.close(
                code=1008,
                reason="Invalid token subject",
            )
            return

        # 2. Verify that the user exists and is active.
        user = db.query(User).filter(
            User.id == user_id
        ).first()

        if not user or not user.is_active:
            await websocket.close(
                code=1008,
                reason="User not found or inactive",
            )
            return

        # 3. Confirm that the requested doctor exists.
        doctor = db.query(Doctor).filter(
            Doctor.id == doctor_id
        ).first()

        if not doctor:
            await websocket.close(
                code=1008,
                reason="Doctor not found",
            )
            return

        # 4. Authorize the requested queue.
        # Doctors can access only their own queue.
        # Admins can access any doctor's queue.
        if user.role == "doctor":
            if doctor.user_id != user.id:
                await websocket.close(
                    code=1008,
                    reason="You cannot access another doctor's queue",
                )
                return
        elif user.role != "admin":
            await websocket.close(
                code=1008,
                reason="Not authorized to access the live queue",
            )
            return

        # 5. Accept only after authentication and authorization.
        await manager.connect(doctor_id, websocket)
        connected = True

        # 6. Send the initial queue snapshot.
        appointments = (
            db.query(Appointment)
            .filter(
                Appointment.doctor_id == doctor_id,
                Appointment.status.in_(["scheduled", "confirmed"]),
            )
            .order_by(Appointment.appointment_datetime.asc())
            .all()
        )

        await websocket.send_json({
            "event": "queue_snapshot",
            "doctor_id": doctor_id,
            "appointments": [
                {
                    "appointment_id": item.id,
                    "patient_id": item.patient_id,
                    "appointment_datetime": (
                        item.appointment_datetime.isoformat()
                    ),
                    "status": item.status,
                }
                for item in appointments
            ],
        })

        # 7. Keep the connection open for live updates.
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        pass

    finally:
        if connected:
            manager.disconnect(doctor_id, websocket)

        db.close()
