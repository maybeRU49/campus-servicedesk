from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import (
    create_access_token,
    get_current_user,
    verify_password
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.execute(
        text("""
            SELECT
                u.user_id,
                u.full_name,
                u.email,
                u.password_hash,
                r.role_name
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            WHERE u.email = :email;
        """),
        {"email": form_data.username}
    ).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    user_data = user._mapping

    if not verify_password(
        form_data.password,
        user_data["password_hash"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    access_token = create_access_token(
        subject=str(user_data["user_id"]),
        additional_claims={
            "email": user_data["email"],
            "role": user_data["role_name"]
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "user_id": user_data["user_id"],
            "full_name": user_data["full_name"],
            "email": user_data["email"],
            "role": user_data["role_name"]
        }
    }

@router.get("/me")
def get_logged_in_user(
    current_user: dict = Depends(get_current_user)
):
    return {
        "user": current_user
    }