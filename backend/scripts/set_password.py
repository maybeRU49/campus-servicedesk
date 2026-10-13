import sys
from getpass import getpass

from sqlalchemy import text

from app.database import SessionLocal
from app.security import hash_password


def set_password(email: str) -> None:
    password = getpass("Enter new password: ")
    confirm_password = getpass("Confirm new password: ")

    if password != confirm_password:
        print("Passwords do not match.")
        return

    if len(password) < 8:
        print("Password must contain at least 8 characters.")
        return

    db = SessionLocal()

    try:
        user = db.execute(
            text("""
                SELECT user_id
                FROM users
                WHERE email = :email
            """),
            {"email": email}
        ).first()

        if user is None:
            print(f"No user found with email: {email}")
            return

        db.execute(
            text("""
                UPDATE users
                SET password_hash = :password_hash
                WHERE email = :email
            """),
            {
                "email": email,
                "password_hash": hash_password(password)
            }
        )

        db.commit()
        print(f"Password updated for {email}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/set_password.py <email>")
        raise SystemExit(1)

    set_password(sys.argv[1])
