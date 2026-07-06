from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(
    prefix="/tickets",
    tags=["Tickets"]
)


class TicketCreate(BaseModel):
    title: str
    description: str
    category: str
    priority: str = "MEDIUM"
    requester_id: int
    department_id: Optional[int] = None
    asset_id: Optional[int] = None

class TicketStatusUpdate(BaseModel):
    new_status: str
    changed_by_user_id: int

class TicketAssignmentCreate(BaseModel):
    technician_id: int
    changed_by_user_id: int

class TicketCommentCreate(BaseModel):
    user_id: int
    comment_text: str

@router.get("/")
def get_tickets(db: Session = Depends(get_db)):
    query = text("""
        SELECT 
            ticket_id,
            title,
            category,
            priority,
            status,
            requester,
            department_name,
            asset_name,
            assigned_technician,
            created_at,
            updated_at,
            resolved_at
        FROM vw_ticket_details
        ORDER BY created_at DESC;
    """)

    result = db.execute(query)
    tickets = [dict(row._mapping) for row in result]

    return {
        "count": len(tickets),
        "tickets": tickets
    }

@router.get("/{ticket_id}")
def get_ticket_by_id(
    ticket_id: int,
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT
            ticket_id,
            title,
            category,
            priority,
            status,
            requester,
            department_name,
            asset_name,
            assigned_technician,
            created_at,
            updated_at,
            resolved_at
        FROM vw_ticket_details
        WHERE ticket_id = :ticket_id;
    """)

    result = db.execute(query, {"ticket_id": ticket_id}).first()

    if result is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return {
        "ticket": dict(result._mapping)
    }
@router.post("/")
def create_ticket(ticket: TicketCreate, db: Session = Depends(get_db)):
    try:
        insert_query = text("""
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
        """)

        result = db.execute(insert_query, ticket.model_dump())
        db.commit()

        new_ticket_id = result.lastrowid

        select_query = text("""
            SELECT 
                ticket_id,
                title,
                category,
                priority,
                status,
                requester,
                department_name,
                asset_name,
                assigned_technician,
                created_at,
                updated_at,
                resolved_at
            FROM vw_ticket_details
            WHERE ticket_id = :ticket_id;
        """)

        created_ticket = db.execute(
            select_query,
            {"ticket_id": new_ticket_id}
        ).first()

        return {
            "message": "Ticket created successfully",
            "ticket": dict(created_ticket._mapping)
        }

    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Could not create ticket: {str(error)}"
        )
    
@router.put("/{ticket_id}/status")
def update_ticket_status(
    ticket_id: int,
    status_update: TicketStatusUpdate,
    db: Session = Depends(get_db)
):
    allowed_statuses = {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"}
    new_status = status_update.new_status.upper()

    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Use OPEN, IN_PROGRESS, RESOLVED, or CLOSED."
        )

    try:
        current_ticket = db.execute(
            text("SELECT status FROM tickets WHERE ticket_id = :ticket_id"),
            {"ticket_id": ticket_id}
        ).first()

        if current_ticket is None:
            raise HTTPException(status_code=404, detail="Ticket not found")

        old_status = current_ticket._mapping["status"]

        update_query = text("""
            UPDATE tickets
            SET 
                status = :new_status,
                resolved_at = CASE 
                    WHEN :new_status = 'RESOLVED' THEN CURRENT_TIMESTAMP
                    ELSE resolved_at
                END
            WHERE ticket_id = :ticket_id;
        """)

        history_query = text("""
            INSERT INTO ticket_status_history (
                ticket_id,
                old_status,
                new_status,
                changed_by_user_id
            )
            VALUES (
                :ticket_id,
                :old_status,
                :new_status,
                :changed_by_user_id
            );
        """)

        db.execute(update_query, {
            "ticket_id": ticket_id,
            "new_status": new_status
        })

        db.execute(history_query, {
            "ticket_id": ticket_id,
            "old_status": old_status,
            "new_status": new_status,
            "changed_by_user_id": status_update.changed_by_user_id
        })

        db.commit()

        updated_ticket = db.execute(
            text("SELECT * FROM vw_ticket_details WHERE ticket_id = :ticket_id"),
            {"ticket_id": ticket_id}
        ).first()

        return {
            "message": "Ticket status updated successfully",
            "ticket": dict(updated_ticket._mapping)
        }

    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Could not update ticket status: {str(error)}"
        )
    
@router.get("/{ticket_id}/history")
def get_ticket_status_history(
    ticket_id: int,
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT
            h.history_id,
            h.ticket_id,
            h.old_status,
            h.new_status,
            u.full_name AS changed_by,
            h.changed_at
        FROM ticket_status_history h
        JOIN users u ON h.changed_by_user_id = u.user_id
        WHERE h.ticket_id = :ticket_id
        ORDER BY h.changed_at DESC;
    """)

    result = db.execute(query, {"ticket_id": ticket_id})
    history = [dict(row._mapping) for row in result]

    return {
        "ticket_id": ticket_id,
        "count": len(history),
        "history": history
    }

@router.post("/{ticket_id}/assign")
def assign_ticket(
    ticket_id: int,
    assignment: TicketAssignmentCreate,
    db: Session = Depends(get_db)
):
    try:
        ticket = db.execute(
            text("SELECT status FROM tickets WHERE ticket_id = :ticket_id"),
            {"ticket_id": ticket_id}
        ).first()

        if ticket is None:
            raise HTTPException(status_code=404, detail="Ticket not found")

        technician = db.execute(
            text("SELECT technician_id FROM technicians WHERE technician_id = :technician_id"),
            {"technician_id": assignment.technician_id}
        ).first()

        if technician is None:
            raise HTTPException(status_code=404, detail="Technician not found")

        existing_assignment = db.execute(
            text("SELECT assignment_id FROM ticket_assignments WHERE ticket_id = :ticket_id"),
            {"ticket_id": ticket_id}
        ).first()

        if existing_assignment is not None:
            raise HTTPException(status_code=400, detail="Ticket is already assigned")

        old_status = ticket._mapping["status"]
        new_status = "IN_PROGRESS" if old_status == "OPEN" else old_status

        db.execute(
            text("""
                INSERT INTO ticket_assignments (
                    ticket_id,
                    technician_id
                )
                VALUES (
                    :ticket_id,
                    :technician_id
                );
            """),
            {
                "ticket_id": ticket_id,
                "technician_id": assignment.technician_id
            }
        )

        if old_status != new_status:
            db.execute(
                text("""
                    UPDATE tickets
                    SET status = :new_status
                    WHERE ticket_id = :ticket_id;
                """),
                {
                    "ticket_id": ticket_id,
                    "new_status": new_status
                }
            )

            db.execute(
                text("""
                    INSERT INTO ticket_status_history (
                        ticket_id,
                        old_status,
                        new_status,
                        changed_by_user_id
                    )
                    VALUES (
                        :ticket_id,
                        :old_status,
                        :new_status,
                        :changed_by_user_id
                    );
                """),
                {
                    "ticket_id": ticket_id,
                    "old_status": old_status,
                    "new_status": new_status,
                    "changed_by_user_id": assignment.changed_by_user_id
                }
            )

        db.commit()

        return {
            "message": "Ticket assigned successfully",
            "ticket_id": ticket_id,
            "technician_id": assignment.technician_id,
            "status": new_status
        }

    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Could not assign ticket: {str(error)}"
        )
@router.get("/{ticket_id}/comments")
def get_ticket_comments(
    ticket_id: int,
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT
            c.comment_id,
            c.ticket_id,
            u.full_name AS commented_by,
            c.comment_text,
            c.created_at
        FROM ticket_comments c
        JOIN users u ON c.user_id = u.user_id
        WHERE c.ticket_id = :ticket_id
        ORDER BY c.created_at ASC;
    """)

    result = db.execute(query, {"ticket_id": ticket_id})
    comments = [dict(row._mapping) for row in result]

    return {
        "ticket_id": ticket_id,
        "count": len(comments),
        "comments": comments
    }


@router.post("/{ticket_id}/comments")
def add_ticket_comment(
    ticket_id: int,
    comment: TicketCommentCreate,
    db: Session = Depends(get_db)
):
    ticket = db.execute(
        text("SELECT ticket_id FROM tickets WHERE ticket_id = :ticket_id"),
        {"ticket_id": ticket_id}
    ).first()

    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    user = db.execute(
        text("SELECT user_id FROM users WHERE user_id = :user_id"),
        {"user_id": comment.user_id}
    ).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        insert_query = text("""
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
        """)

        result = db.execute(insert_query, {
            "ticket_id": ticket_id,
            "user_id": comment.user_id,
            "comment_text": comment.comment_text
        })

        db.commit()

        return {
            "message": "Comment added successfully",
            "comment_id": result.lastrowid,
            "ticket_id": ticket_id
        }

    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Could not add comment: {str(error)}"
        )