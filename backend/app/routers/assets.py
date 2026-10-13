from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.access import ticket_scope
from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/assets", tags=["Assets"])
ASSET_SELECT = """
    SELECT a.asset_id, a.asset_tag, a.asset_name, a.asset_type, a.status,
           a.department_id, d.department_name, a.created_at
    FROM assets a LEFT JOIN departments d ON d.department_id = a.department_id
"""


@router.get("/")
def list_assets(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assets = db.execute(text(ASSET_SELECT + " ORDER BY a.asset_name, a.asset_id")).mappings().all()
    return {"count": len(assets), "assets": [dict(asset) for asset in assets]}


@router.get("/{asset_id}")
def asset_detail(
    asset_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    asset = db.execute(text(ASSET_SELECT + " WHERE a.asset_id = :asset_id"),
                       {"asset_id": asset_id}).mappings().first()
    if asset is None:
        raise HTTPException(404, "Asset not found")
    scope, params = ticket_scope(current_user)
    tickets = db.execute(text(f"""
        SELECT v.* FROM vw_ticket_details v
        JOIN tickets t ON t.ticket_id = v.ticket_id
        WHERE t.asset_id = :asset_id AND ({scope})
        ORDER BY v.created_at DESC, v.ticket_id DESC
    """), {**params, "asset_id": asset_id}).mappings().all()
    return {"asset": dict(asset), "count": len(tickets),
            "tickets": [dict(ticket) for ticket in tickets]}
