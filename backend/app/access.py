"""One server-side ticket visibility policy for every read and write route."""
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session


def ticket_scope(user: dict) -> tuple[str, dict]:
    # Fixed SQL fragments only; all user values remain bound parameters.
    role = user["role_name"]
    if role == "ADMIN":
        return "1 = 1", {}
    if role == "TECHNICIAN":
        return """EXISTS (
            SELECT 1 FROM ticket_assignments scope_assignment
            JOIN technicians scope_tech
              ON scope_tech.technician_id = scope_assignment.technician_id
            WHERE scope_assignment.ticket_id = t.ticket_id
              AND scope_tech.user_id = :scope_user_id
        )""", {"scope_user_id": user["user_id"]}
    if role in {"STUDENT", "STAFF"}:
        return "t.requester_id = :scope_user_id", {"scope_user_id": user["user_id"]}
    raise HTTPException(403, "Unsupported role")


def require_ticket_access(db: Session, ticket_id: int, user: dict, *, lock=False):
    scope, params = ticket_scope(user)
    # Serialize assignment/status changes on the parent ticket in MySQL.
    suffix = " FOR UPDATE" if lock and db.bind.dialect.name == "mysql" else ""
    ticket = db.execute(text(f"""
        SELECT t.ticket_id, t.status FROM tickets t
        WHERE t.ticket_id = :ticket_id AND ({scope}){suffix}
    """), {**params, "ticket_id": ticket_id}).mappings().first()
    if ticket is None:
        # Same response for nonexistent and inaccessible IDs.
        raise HTTPException(404, "Ticket not found")
    return ticket
