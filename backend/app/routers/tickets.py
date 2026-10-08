from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import get_current_user, require_roles


router = APIRouter(
    prefix="/tickets",
    tags=["Tickets"]
)


class TicketCreate(BaseModel):
    title: str = Field(
        min_length=3,
        max_length=150
    )

    description: str = Field(
        min_length=5,
        max_length=2000
    )

    category: Literal[
        "Hardware",
        "Software",
        "Network",
        "Access",
        "Other"
    ]

    priority: Literal[
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL"
    ] = "MEDIUM"

    department_id: Optional[int] = Field(
        default=None,
        gt=0
    )

    asset_id: Optional[int] = Field(
        default=None,
        gt=0
    )


class TicketStatusUpdate(BaseModel):
    new_status: Literal[
        "OPEN",
        "IN_PROGRESS",
        "RESOLVED",
        "CLOSED"
    ]


class TicketAssignmentCreate(BaseModel):
    technician_id: int = Field(gt=0)


class TicketCommentCreate(BaseModel):
    comment_text: str = Field(
        min_length=2,
        max_length=1000
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
    result = db.execute(
        text("""
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
    try:
        ticket_data = ticket.model_dump()

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

        db.commit()

        new_ticket_id = result.lastrowid

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

    except SQLAlchemyError as error:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=(
                "Could not create ticket: "
                f"{str(error)}"
            )
        )


@router.put("/{ticket_id}/status")
def update_ticket_status(
    ticket_id: int,
    status_update: TicketStatusUpdate,
    current_user: dict = Depends(
        require_roles(
            "ADMIN",
            "TECHNICIAN"
        )
    ),
    db: Session = Depends(get_db)
):
    new_status = status_update.new_status

    try:
        current_ticket = db.execute(
            text("""
                SELECT status
                FROM tickets
                WHERE ticket_id = :ticket_id;
            """),
            {
                "ticket_id": ticket_id
            }
        ).first()

        if current_ticket is None:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found"
            )

        old_status = (
            current_ticket
            ._mapping["status"]
        )

        if old_status == new_status:
            return {
                "message":
                    "Ticket already has this status",
                "ticket":
                    get_ticket_detail(
                        db,
                        ticket_id
                    )
            }

        db.execute(
            text("""
                UPDATE tickets
                SET
                    status = :new_status,

                    resolved_at =
                        CASE
                            WHEN :new_status
                                IN (
                                    'RESOLVED',
                                    'CLOSED'
                                )
                            THEN COALESCE(
                                resolved_at,
                                CURRENT_TIMESTAMP
                            )
                            ELSE NULL
                        END

                WHERE ticket_id = :ticket_id;
            """),
            {
                "ticket_id": ticket_id,
                "new_status": new_status
            }
        )

        db.execute(
            text("""
                INSERT INTO
                    ticket_status_history (
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
                "changed_by_user_id":
                    current_user["user_id"]
            }
        )

        db.commit()

        return {
            "message":
                "Ticket status updated successfully",
            "ticket":
                get_ticket_detail(
                    db,
                    ticket_id
                )
        }

    except SQLAlchemyError as error:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=(
                "Could not update ticket status: "
                f"{str(error)}"
            )
        )


@router.get("/{ticket_id}/history")
def get_ticket_status_history(
    ticket_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ticket = db.execute(
        text("""
            SELECT ticket_id
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

            ORDER BY h.changed_at DESC;
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
    try:
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
                    technician_id,
                    is_available
                FROM technicians
                WHERE technician_id =
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
                    SET technician_id =
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

        old_status = (
            ticket
            ._mapping["status"]
        )

        new_status = (
            "IN_PROGRESS"
            if old_status == "OPEN"
            else old_status
        )

        if old_status != new_status:
            db.execute(
                text("""
                    UPDATE tickets
                    SET status = :new_status
                    WHERE ticket_id =
                        :ticket_id;
                """),
                {
                    "ticket_id":
                        ticket_id,
                    "new_status":
                        new_status
                }
            )

            db.execute(
                text("""
                    INSERT INTO
                        ticket_status_history (
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
                    "ticket_id":
                        ticket_id,
                    "old_status":
                        old_status,
                    "new_status":
                        new_status,
                    "changed_by_user_id":
                        current_user["user_id"]
                }
            )

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

    except SQLAlchemyError as error:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=(
                "Could not assign ticket: "
                f"{str(error)}"
            )
        )


@router.get("/{ticket_id}/comments")
def get_ticket_comments(
    ticket_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ticket = db.execute(
        text("""
            SELECT ticket_id
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

            ORDER BY c.created_at ASC;
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
    ticket = db.execute(
        text("""
            SELECT ticket_id
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

    try:
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

    except SQLAlchemyError as error:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=(
                "Could not add comment: "
                f"{str(error)}"
            )
        )