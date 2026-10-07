from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    total_tickets = db.execute(
        text("SELECT COUNT(*) FROM tickets")
    ).scalar()

    open_tickets = db.execute(
        text("SELECT COUNT(*) FROM tickets WHERE status = 'OPEN'")
    ).scalar()

    in_progress_tickets = db.execute(
        text("SELECT COUNT(*) FROM tickets WHERE status = 'IN_PROGRESS'")
    ).scalar()

    resolved_tickets = db.execute(
        text("SELECT COUNT(*) FROM tickets WHERE status = 'RESOLVED'")
    ).scalar()

    high_priority_tickets = db.execute(
        text("SELECT COUNT(*) FROM tickets WHERE priority = 'HIGH'")
    ).scalar()

    unassigned_tickets = db.execute(
        text("""
            SELECT COUNT(*)
            FROM tickets t
            LEFT JOIN ticket_assignments ta ON t.ticket_id = ta.ticket_id
            WHERE ta.assignment_id IS NULL;
        """)
    ).scalar()

    tickets_by_status = db.execute(
        text("""
            SELECT status, COUNT(*) AS count
            FROM tickets
            GROUP BY status;
        """)
    )

    tickets_by_category = db.execute(
        text("""
            SELECT category, COUNT(*) AS count
            FROM tickets
            GROUP BY category;
        """)
    )

    return {
        "total_tickets": total_tickets,
        "open_tickets": open_tickets,
        "in_progress_tickets": in_progress_tickets,
        "resolved_tickets": resolved_tickets,
        "high_priority_tickets": high_priority_tickets,
        "unassigned_tickets": unassigned_tickets,
        "tickets_by_status": [dict(row._mapping) for row in tickets_by_status],
        "tickets_by_category": [dict(row._mapping) for row in tickets_by_category]
    }