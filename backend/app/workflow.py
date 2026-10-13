"""Ticket relationship validation and atomic lifecycle operations."""
from fastapi import HTTPException
from sqlalchemy import text

TRANSITIONS = {
    "OPEN": {"IN_PROGRESS"},
    "IN_PROGRESS": {"OPEN", "RESOLVED"},
    "RESOLVED": {"IN_PROGRESS", "CLOSED"},
    "CLOSED": {"OPEN"},
}


def validate_ticket_references(db, data):
    department_id = data["department_id"]
    if department_id is not None:
        found = db.execute(text(
            "SELECT department_id FROM departments WHERE department_id = :id"
        ), {"id": department_id}).first()
        if found is None:
            raise HTTPException(422, "Department not found")
    if data["asset_id"] is not None:
        asset = db.execute(text(
            "SELECT department_id FROM assets WHERE asset_id = :id"
        ), {"id": data["asset_id"]}).mappings().first()
        if asset is None:
            raise HTTPException(422, "Asset not found")
        if department_id is not None and department_id != asset["department_id"]:
            raise HTTPException(422, "Asset does not belong to the selected department")
        if department_id is None:
            data["department_id"] = asset["department_id"]


def record_history(db, ticket_id, old_status, new_status, user_id):
    db.execute(text("""
        INSERT INTO ticket_status_history
          (ticket_id, old_status, new_status, changed_by_user_id)
        VALUES (:ticket_id, :old_status, :new_status, :user_id)
    """), dict(ticket_id=ticket_id, old_status=old_status,
               new_status=new_status, user_id=user_id))


def change_status(db, ticket_id, old_status, new_status, user):
    if old_status == new_status:
        return False
    if new_status not in TRANSITIONS.get(old_status, set()):
        raise HTTPException(409, f"Cannot change status from {old_status} to {new_status}")
    if old_status == "CLOSED" and user["role_name"] != "ADMIN":
        raise HTTPException(403, "Only an administrator can reopen a closed ticket")
    db.execute(text("""
        UPDATE tickets SET status = :new_status, updated_at = CURRENT_TIMESTAMP,
          resolved_at = CASE
            WHEN :new_status IN ('RESOLVED', 'CLOSED')
            THEN COALESCE(resolved_at, CURRENT_TIMESTAMP)
            ELSE NULL END
        WHERE ticket_id = :ticket_id
    """), {"ticket_id": ticket_id, "new_status": new_status})
    record_history(db, ticket_id, old_status, new_status, user["user_id"])
    return True
