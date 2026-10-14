
from getpass import getpass

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User
from app.utils.security import hash_password


def main():
    full_name = input("Admin full name: ").strip()
    email = input("Admin email: ").strip().lower()
    password = getpass("Admin password (minimum 8 characters): ")

    if len(password) < 8:
        print("Password must be at least 8 characters.")
        return

    db: Session = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()

        if existing:
            print("This email already exists. No changes made.")
            return

        admin = User(
            full_name=full_name,
            email=email,
            hashed_password=hash_password(password),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print("Admin account created successfully.")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
