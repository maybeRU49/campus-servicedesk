from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.access import ticket_scope
from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def get_dashboard_summary(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scope, params = ticket_scope(current_user)
    summary = dict(db.execute(text(f"""
        SELECT COUNT(*) AS total_tickets,
          COALESCE(SUM(CASE WHEN t.status = 'OPEN' THEN 1 ELSE 0 END), 0) AS open_tickets,
          COALESCE(SUM(CASE WHEN t.status = 'IN_PROGRESS' THEN 1 ELSE 0 END), 0) AS in_progress_tickets,
          COALESCE(SUM(CASE WHEN t.status = 'RESOLVED' THEN 1 ELSE 0 END), 0) AS resolved_tickets,
          COALESCE(SUM(CASE WHEN t.status = 'CLOSED' THEN 1 ELSE 0 END), 0) AS closed_tickets,
          COALESCE(SUM(CASE WHEN t.priority IN ('HIGH', 'CRITICAL') THEN 1 ELSE 0 END), 0) AS high_priority_tickets,
          COALESCE(SUM(CASE WHEN NOT EXISTS (
            SELECT 1 FROM ticket_assignments ta WHERE ta.ticket_id = t.ticket_id
          ) THEN 1 ELSE 0 END), 0) AS unassigned_tickets
        FROM tickets t WHERE {scope}
    """), params).mappings().one())
    for field in ("status", "category"):
        rows = db.execute(text(f"""
            SELECT t.{field}, COUNT(*) AS count FROM tickets t
            WHERE {scope} GROUP BY t.{field} ORDER BY t.{field}
        """), params).mappings().all()
        summary[f"tickets_by_{field}"] = [dict(row) for row in rows]
    summary["scope"] = {
        "ADMIN": "All campus tickets", "TECHNICIAN": "Assigned to me",
        "STUDENT": "My tickets", "STAFF": "My tickets",
    }[current_user["role_name"]]
    return summary
