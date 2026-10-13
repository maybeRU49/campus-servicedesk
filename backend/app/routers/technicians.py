from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import get_current_user


router = APIRouter(
    prefix="/technicians",
    tags=["Technicians"]
)


@router.get("/")
def get_technicians(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    result = db.execute(
        text("""
            SELECT
                t.technician_id,
                u.full_name,
                u.email,
                t.specialization,
                t.is_available
            FROM technicians t
            JOIN users u
                ON t.user_id = u.user_id
            ORDER BY u.full_name
        """)
    )

    technicians = [
        dict(row._mapping)
        for row in result
    ]

    return {
        "count": len(technicians),
        "technicians": technicians
    }
