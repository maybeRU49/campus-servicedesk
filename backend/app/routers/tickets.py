from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.access import require_ticket_access, ticket_scope
from app.security import get_current_user, require_roles
from app.schemas import (TicketCreate, TicketStatusUpdate, TicketAssignmentCreate, TicketCommentCreate)
from app.workflow import change_status, record_history, validate_ticket_references


router = APIRouter(
    prefix="/tickets",
    tags=["Tickets"]
)


def get_ticket_detail(
    db: Session,
    ticket_id: int
):
    result = db.execute(
        text("""
            SELECT
                v.ticket_id,
                v.title,
                t.description,
                v.category,
                v.priority,
                v.status,
                v.requester,
                v.department_name,
                v.asset_name,
                v.assigned_technician,
                v.created_at,
                v.updated_at,
                v.resolved_at
            FROM vw_ticket_details v
            JOIN tickets t
                ON v.ticket_id = t.ticket_id
            WHERE v.ticket_id = :ticket_id;
        """),
        {
            "ticket_id": ticket_id
        }
    ).first()

    if result is None:
        return None

    return dict(result._mapping)


@router.get("/")
def get_tickets(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    scope, params = ticket_scope(current_user)
    result = db.execute(
        text(f"""
            SELECT
                v.ticket_id,
                v.title,
                v.category,
                v.priority,
                v.status,
                v.requester,
                v.department_name,
                v.asset_name,
                v.assigned_technician,
                v.created_at,
                v.updated_at,
                v.resolved_at
            FROM vw_ticket_details v
            JOIN tickets t ON t.ticket_id = v.ticket_id
            WHERE {scope}
            ORDER BY v.created_at DESC, v.ticket_id DESC;
        """), params
    )

    tickets = [
        dict(row._mapping)
        for row in result
    ]

    return {
        "count": len(tickets),
        "tickets": tickets
    }


@router.get("/{ticket_id}")
def get_ticket_by_id(
    ticket_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    require_ticket_access(db, ticket_id, current_user)
    ticket = get_ticket_detail(
        db,
        ticket_id
    )

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    return {
        "ticket": ticket
    }


@router.post("/")
def create_ticket(
    ticket: TicketCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ticket_data = ticket.model_dump()
    validate_ticket_references(db, ticket_data)

    ticket_data["requester_id"] = (
        current_user["user_id"]
    )

    result = db.execute(
        text("""
            INSERT INTO tickets (
                title,
                description,
                category,
                priority,
                status,
                requester_id,
                department_id,
                asset_id
            )
            VALUES (
                :title,
                :description,
                :category,
                :priority,
                'OPEN',
                :requester_id,
                :department_id,
                :asset_id
            );
        """),
        ticket_data
    )

    new_ticket_id = result.lastrowid
    record_history(db, new_ticket_id, None, "OPEN", current_user["user_id"])
    db.commit()

    created_ticket = get_ticket_detail(
        db,
        new_ticket_id
    )

    return {
        "message":
            "Ticket created successfully",
        "ticket":
            created_ticket
    }



@router.put("/{ticket_id}/status")
def update_ticket_status(
    ticket_id: int,
    status_update: TicketStatusUpdate,
    current_user: dict = Depends(require_roles("ADMIN", "TECHNICIAN")),
    db: Session = Depends(get_db),
):
    ticket = require_ticket_access(db, ticket_id, current_user, lock=True)
    changed = change_status(db, ticket_id, ticket["status"], status_update.new_status, current_user)
    db.commit()
    return {
        "message": "Ticket status updated successfully" if changed else "Ticket already has this status",
        "ticket": get_ticket_detail(db, ticket_id),
    }


@router.get("/{ticket_id}/history")
def get_ticket_status_history(
    ticket_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    require_ticket_access(db, ticket_id, current_user)

    result = db.execute(
        text("""
            SELECT
                h.history_id,
                h.ticket_id,
                h.old_status,
                h.new_status,
                u.full_name AS changed_by,
                h.changed_at

            FROM ticket_status_history h

            JOIN users u
                ON h.changed_by_user_id =
                   u.user_id

            WHERE h.ticket_id = :ticket_id

            ORDER BY h.changed_at DESC, h.history_id DESC;
        """),
        {
            "ticket_id": ticket_id
        }
    )

    history = [
        dict(row._mapping)
        for row in result
    ]

    return {
        "ticket_id": ticket_id,
        "count": len(history),
        "history": history
    }


@router.post("/{ticket_id}/assign")
def assign_ticket(
    ticket_id: int,
    assignment: TicketAssignmentCreate,
    current_user: dict = Depends(
        require_roles("ADMIN")
    ),
    db: Session = Depends(get_db)
):
    require_ticket_access(db, ticket_id, current_user, lock=True)
    ticket = db.execute(
        text("""
            SELECT status
            FROM tickets
            WHERE ticket_id = :ticket_id;
        """),
        {
            "ticket_id": ticket_id
        }
    ).first()

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    technician = db.execute(
        text("""
            SELECT
                tech.technician_id,
                tech.is_available
            FROM technicians tech
            JOIN users u ON tech.user_id = u.user_id
            JOIN roles r ON u.role_id = r.role_id
            WHERE r.role_name = 'TECHNICIAN' AND tech.technician_id =
                :technician_id;
        """),
        {
            "technician_id":
                assignment.technician_id
        }
    ).first()

    if technician is None:
        raise HTTPException(
            status_code=404,
            detail="Technician not found"
        )

    if not technician._mapping[
        "is_available"
    ]:
        raise HTTPException(
            status_code=400,
            detail=(
                "Selected technician "
                "is unavailable"
            )
        )

    existing_assignment = db.execute(
        text("""
            SELECT
                assignment_id,
                technician_id
            FROM ticket_assignments
            WHERE ticket_id = :ticket_id;
        """),
        {
            "ticket_id": ticket_id
        }
    ).first()

    if existing_assignment is None:
        db.execute(
            text("""
                INSERT INTO
                    ticket_assignments (
                        ticket_id,
                        technician_id
                    )
                VALUES (
                    :ticket_id,
                    :technician_id
                );
            """),
            {
                "ticket_id":
                    ticket_id,
                "technician_id":
                    assignment.technician_id
            }
        )

    elif (
        existing_assignment
        ._mapping["technician_id"]
        != assignment.technician_id
    ):
        db.execute(
            text("""
                UPDATE ticket_assignments
                SET assigned_at = CURRENT_TIMESTAMP, technician_id =
                    :technician_id
                WHERE ticket_id =
                    :ticket_id;
            """),
            {
                "ticket_id":
                    ticket_id,
                "technician_id":
                    assignment.technician_id
            }
        )

    old_status = ticket._mapping["status"]
    if old_status == "OPEN":
        change_status(db, ticket_id, old_status, "IN_PROGRESS", current_user)

    db.commit()

    return {
        "message":
            "Ticket assigned successfully",
        "ticket":
            get_ticket_detail(
                db,
                ticket_id
            )
    }



@router.get("/{ticket_id}/comments")
def get_ticket_comments(
    ticket_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    require_ticket_access(db, ticket_id, current_user)

    result = db.execute(
        text("""
            SELECT
                c.comment_id,
                c.ticket_id,
                u.full_name AS commented_by,
                c.comment_text,
                c.created_at

            FROM ticket_comments c

            JOIN users u
                ON c.user_id = u.user_id

            WHERE c.ticket_id = :ticket_id

            ORDER BY c.created_at ASC, c.comment_id ASC;
        """),
        {
            "ticket_id": ticket_id
        }
    )

    comments = [
        dict(row._mapping)
        for row in result
    ]

    return {
        "ticket_id": ticket_id,
        "count": len(comments),
        "comments": comments
    }


@router.post("/{ticket_id}/comments")
def add_ticket_comment(
    ticket_id: int,
    comment: TicketCommentCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    require_ticket_access(db, ticket_id, current_user)

    result = db.execute(
        text("""
            INSERT INTO ticket_comments (
                ticket_id,
                user_id,
                comment_text
            )
            VALUES (
                :ticket_id,
                :user_id,
                :comment_text
            );
        """),
        {
            "ticket_id":
                ticket_id,
            "user_id":
                current_user["user_id"],
            "comment_text":
                comment.comment_text
        }
    )

    db.commit()

    return {
        "message":
            "Comment added successfully",
        "comment_id":
            result.lastrowid,
        "ticket_id":
            ticket_id
    }
