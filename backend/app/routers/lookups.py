from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import get_current_user


router = APIRouter(
    prefix="/lookups",
    tags=["Lookups"]
)


@router.get("/departments")
def get_departments(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    result = db.execute(
        text("""
            SELECT
                department_id,
                department_name
            FROM departments
            ORDER BY department_name;
        """)
    )

    departments = [
        dict(row._mapping)
        for row in result
    ]

    return {
        "count": len(departments),
        "departments": departments
    }


@router.get("/assets")
def get_assets(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    result = db.execute(
        text("""
            SELECT
                asset_id,
                asset_name,
                department_id
            FROM assets
            ORDER BY asset_name;
        """)
    )

    assets = [
        dict(row._mapping)
        for row in result
    ]

    return {
        "count": len(assets),
        "assets": assets
    }