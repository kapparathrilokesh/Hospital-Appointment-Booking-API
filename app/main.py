
from fastapi import FastAPI

from app.routers.auth import router as auth_router
from app.routers.departments import router as departments_router
from app.routers.doctors import router as doctors_router
from app.routers import patients
from app.routers import appointments
from app.routers import doctor_schedules
from app.routers import doctor_leaves
from app.routers import consultations
from app.routers import prescriptions
from app.routers import medical_files
from app.routers import live_queue

app = FastAPI(
    title="Hospital Appointment Booking API",
    version="1.0.0",
    description="API for hospital departments, doctors, patients, and appointments.",
)

app.include_router(auth_router)
app.include_router(departments_router)
app.include_router(doctors_router)
app.include_router(patients.router)
app.include_router(appointments.router)
app.include_router(doctor_schedules.router)
app.include_router(doctor_leaves.router)
app.include_router(consultations.router)
app.include_router(prescriptions.router)
app.include_router(medical_files.router)
app.include_router(live_queue.router)


@app.get("/", tags=["Health"])
def health_check():
    return {"message": "Hospital Appointment Booking API is running"}
