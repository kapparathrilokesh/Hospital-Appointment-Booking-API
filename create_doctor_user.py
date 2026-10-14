
from getpass import getpass

from app.database import SessionLocal
from app.models.user import User
from app.utils.security import hash_password


def main():
    full_name = input("Doctor full name: ").strip()
    email = input("Doctor email: ").strip().lower()
    phone = input("Doctor phone (optional): ").strip() or None
    password = getpass("Doctor password (minimum 8 characters): ")

    if not full_name or len(full_name) < 2:
        print("Name must contain at least 2 characters.")
        return

    if len(password) < 8:
        print("Password must contain at least 8 characters.")
        return

    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            print("This email already exists.")
            return

        if phone and db.query(User).filter(User.phone == phone).first():
            print("This phone number already exists.")
            return

        doctor_user = User(
            full_name=full_name,
            email=email,
            phone=phone,
            hashed_password=hash_password(password),
            role="doctor",
            is_active=True,
        )

        db.add(doctor_user)
        db.commit()
        db.refresh(doctor_user)

        print("Doctor user created successfully.")
        print(f"Doctor user ID: {doctor_user.id}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
