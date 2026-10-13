from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import event, text

from app.security import JWT_SECRET_KEY, create_access_token


def ticket_payload(**changes):
    return {"title": "Network outage", "description": "The classroom Wi-Fi is down",
            "category": "Network", "priority": "HIGH", **changes}


@pytest.mark.parametrize("user_id", [1,2,3,4])
def test_valid_login_and_identity(client, headers, user_id):
    response = client.get("/auth/me", headers=headers(user_id))
    assert response.status_code == 200
    user = response.json()["user"]
    assert user["user_id"] == user_id
    assert "password_hash" not in user


@pytest.mark.parametrize("username,password", [
    ("missing@example.com","wrong"), ("user1@example.com","wrong")
])
def test_invalid_login(client, username, password):
    response = client.post("/auth/login",data={"username":username,"password":password})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_seed_placeholder_hash_fails_safely(client, db):
    with db.begin() as session:
        session.execute(text("UPDATE users SET password_hash='dummy_hash' WHERE user_id=1"))
    assert client.post("/auth/login",data={
        "username":"user1@example.com","password":"anything"
    }).status_code == 401


@pytest.mark.parametrize("path", [
    "/auth/me","/tickets/","/tickets/1","/tickets/1/comments","/tickets/1/history",
    "/dashboard/summary","/lookups/departments","/lookups/assets","/technicians/","/assets/","/assets/1","/db-health"
])
def test_sensitive_reads_require_authentication(client, path):
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("method,path,payload", [
    ("post","/tickets/",ticket_payload()),
    ("post","/tickets/1/comments",{"comment_text":"Hello"}),
    ("post","/tickets/1/assign",{"technician_id":1}),
    ("put","/tickets/1/status",{"new_status":"IN_PROGRESS"}),
])
def test_sensitive_writes_require_authentication(client, method, path, payload):
    assert getattr(client,method)(path,json=payload).status_code == 401


@pytest.mark.parametrize("user_id,expected", [(1,{1,2,3,4,5}),(2,{2}),(5,{3}),(3,{2}),(4,{3}),(6,{4}),(7,{5})])
def test_ticket_list_and_dashboard_share_scope(client, headers, user_id, expected):
    auth = headers(user_id)
    tickets = client.get("/tickets/",headers=auth).json()
    assert {ticket["ticket_id"] for ticket in tickets["tickets"]} == expected
    summary = client.get("/dashboard/summary",headers=auth).json()
    assert summary["total_tickets"] == len(expected)
    assert summary["open_tickets"] == len(expected)
    assert summary["high_priority_tickets"] == len(expected)
    assert sum(row["count"] for row in summary["tickets_by_status"]) == len(expected)
    assert sum(row["count"] for row in summary["tickets_by_category"]) == len(expected)


@pytest.mark.parametrize("user_id,allowed,denied", [(3,2,1),(4,3,1),(2,2,3),(6,4,2),(7,5,3)])
@pytest.mark.parametrize("suffix", ["","/comments","/history"])
def test_guessed_ticket_ids_do_not_leak(client,headers,user_id,allowed,denied,suffix):
    auth = headers(user_id)
    assert client.get(f"/tickets/{allowed}{suffix}",headers=auth).status_code == 200
    assert client.get(f"/tickets/{denied}{suffix}",headers=auth).status_code == 404
    assert client.get(f"/tickets/99999{suffix}",headers=auth).status_code == 404


@pytest.mark.parametrize("user_id", [3,4,2])
def test_comment_rejects_inaccessible_ticket(client,headers,user_id):
    assert client.post("/tickets/1/comments",headers=headers(user_id),
                       json={"comment_text":"Private comment"}).status_code == 404


@pytest.mark.parametrize("user_id,ticket_id", [(1,1),(2,2),(3,2),(4,3)])
def test_comment_records_authenticated_author(client,headers,user_id,ticket_id):
    auth = headers(user_id)
    response = client.post(f"/tickets/{ticket_id}/comments",headers=auth,
                           json={"comment_text":"  Please investigate  "})
    assert response.status_code == 200
    comment = client.get(f"/tickets/{ticket_id}/comments",headers=auth).json()["comments"][-1]
    assert comment["commented_by"] == f"User {user_id}"
    assert comment["comment_text"] == "Please investigate"


@pytest.mark.parametrize("user_id", [2,3,4])
def test_only_admin_can_assign(client,headers,user_id):
    assert client.post("/tickets/2/assign",headers=headers(user_id),
                       json={"technician_id":1}).status_code == 403


@pytest.mark.parametrize("user_id,ticket_id", [(3,2),(4,3)])
def test_requesters_cannot_change_status(client,headers,user_id,ticket_id):
    assert client.put(f"/tickets/{ticket_id}/status",headers=headers(user_id),
                      json={"new_status":"IN_PROGRESS"}).status_code == 403


def test_technician_cannot_change_other_work(client,headers):
    assert client.put("/tickets/3/status",headers=headers(2),
                      json={"new_status":"IN_PROGRESS"}).status_code == 404
    assert client.put("/tickets/1/status",headers=headers(2),
                      json={"new_status":"IN_PROGRESS"}).status_code == 404


@pytest.mark.parametrize("user_id", [1,2,3,4])
def test_creation_and_relationships(client,headers,user_id):
    auth = headers(user_id)
    response = client.post("/tickets/",headers=auth,json=ticket_payload(asset_id=1))
    assert response.status_code == 200
    ticket = response.json()["ticket"]
    assert ticket["requester"] == f"User {user_id}"
    assert ticket["asset_name"] == "Lab PC"
    assert ticket["department_name"] == "IT Services"
    # Technicians see only assigned work, including for their own requests.
    visible = headers(1) if user_id == 2 else auth
    history = client.get(f"/tickets/{ticket['ticket_id']}/history",headers=visible).json()["history"]
    assert history[0]["old_status"] is None and history[0]["new_status"] == "OPEN"


@pytest.mark.parametrize("changes", [
    {"title":"  "},{"description":"x"},{"category":"Invalid"},{"priority":"URGENT"},
    {"department_id":0},{"department_id":999},{"asset_id":999},
    {"department_id":1,"asset_id":2},{"requester_id":1}
])
def test_ticket_validation(client,headers,changes):
    response = client.post("/tickets/",headers=headers(3),json=ticket_payload(**changes))
    assert response.status_code == 422


def test_assignment_reassignment_lifecycle_history(client,headers):
    admin, tech1, tech2 = headers(1), headers(2), headers(5)
    result = client.post("/tickets/1/assign",headers=admin,json={"technician_id":1})
    assert result.status_code == 200
    assert result.json()["ticket"]["status"] == "IN_PROGRESS"
    assert client.post("/tickets/1/assign",headers=admin,json={"technician_id":2}).status_code == 200
    assert client.get("/tickets/1",headers=tech1).status_code == 404
    assert client.get("/tickets/1",headers=tech2).status_code == 200
    for status in ["RESOLVED","CLOSED"]:
        response = client.put("/tickets/1/status",headers=tech2,json={"new_status":status})
        assert response.status_code == 200
        assert response.json()["ticket"]["resolved_at"] is not None
    assert client.put("/tickets/1/status",headers=tech2,json={"new_status":"OPEN"}).status_code == 403
    result = client.put("/tickets/1/status",headers=admin,json={"new_status":"OPEN"})
    assert result.json()["ticket"]["resolved_at"] is None
    history = client.get("/tickets/1/history",headers=admin).json()["history"]
    assert len(history) == 4
    assert history[0]["changed_by"] == "User 1"


def test_invalid_transition_and_idempotence(client,headers):
    auth = headers(1)
    assert client.put("/tickets/1/status",headers=auth,json={"new_status":"CLOSED"}).status_code == 409
    assert client.put("/tickets/1/status",headers=auth,json={"new_status":"OPEN"}).status_code == 200
    assert client.get("/tickets/1/history",headers=auth).json()["count"] == 0


def test_assignment_validation(client,headers,db):
    auth = headers(1)
    assert client.post("/tickets/1/assign",headers=auth,json={"technician_id":999}).status_code == 404
    assert client.post("/tickets/1/assign",headers=auth,json={"technician_id":0}).status_code == 422
    with db.begin() as session:
        session.execute(text("UPDATE technicians SET is_available=0 WHERE technician_id=1"))
    assert client.post("/tickets/1/assign",headers=auth,json={"technician_id":1}).status_code == 400
    with db.begin() as session:
        session.execute(text("UPDATE users SET role_id=3 WHERE user_id=5"))
    assert client.post("/tickets/1/assign",headers=auth,json={"technician_id":2}).status_code == 404


@pytest.mark.parametrize("user_id,expected", [(1,{1,2,3,4,5}),(2,{2}),(3,{2}),(4,{3})])
def test_assets_linked_tickets_are_scoped(client,headers,user_id,expected):
    auth = headers(user_id)
    assets = client.get("/assets/",headers=auth).json()["assets"]
    assert assets[0]["asset_type"] and assets[0]["asset_tag"]
    result = client.get("/assets/1",headers=auth).json()
    assert {t["ticket_id"] for t in result["tickets"]} == expected
    assert client.get("/assets/999",headers=auth).status_code == 404


@pytest.mark.parametrize("claims", [
    {"sub":"3"},
    {"sub":"3","exp":datetime.now(timezone.utc)-timedelta(seconds=1)},
    {"sub":"invalid","exp":datetime.now(timezone.utc)+timedelta(minutes=5)},
    {"sub":"999","exp":datetime.now(timezone.utc)+timedelta(minutes=5)}
])
def test_invalid_tokens(client,claims):
    token = jwt.encode(claims,JWT_SECRET_KEY,algorithm="HS256")
    assert client.get("/tickets/",headers={"Authorization":"Bearer "+token}).status_code == 401


def test_tampered_token_and_current_role(client,headers,db):
    assert client.get("/tickets/",headers={"Authorization":"Bearer tampered"}).status_code == 401
    auth = headers(1)
    with db.begin() as session:
        session.execute(text("UPDATE users SET role_id=3 WHERE user_id=1"))
    # The old token's ADMIN claim must never override current database permissions.
    assert client.post("/tickets/2/assign",headers=auth,json={"technician_id":1}).status_code == 403


def test_protected_claims_cannot_be_overridden():
    token = create_access_token("3", {"sub":"1","exp":0})
    claims = jwt.decode(token,JWT_SECRET_KEY,algorithms=["HS256"])
    assert claims["sub"] == "3" and claims["exp"] > 0


def test_database_failure_rolls_back_status_and_hides_sql(client,headers,db,test_engine):
    auth = headers(1)
    def fail_history(conn,cursor,statement,parameters,context,executemany):
        if "INSERT INTO ticket_status_history" in statement:
            # A genuine database exception exercises dependency rollback and the handler.
            conn.exec_driver_sql("INSERT INTO missing_private_table VALUES ('sensitive')")
    event.listen(test_engine,"before_cursor_execute",fail_history)
    try:
        response = client.put("/tickets/1/status",headers=auth,json={"new_status":"IN_PROGRESS"})
    finally:
        event.remove(test_engine,"before_cursor_execute",fail_history)
    assert response.status_code == 503
    assert "sensitive" not in response.text and "missing_private_table" not in response.text
    with db() as session:
        assert session.execute(text("SELECT status FROM tickets WHERE ticket_id=1")).scalar() == "OPEN"
        assert session.execute(text("SELECT COUNT(*) FROM ticket_status_history")).scalar() == 0


def test_database_health_is_admin_only(client,headers):
    assert client.get("/db-health",headers=headers(3)).status_code == 403


def test_empty_dashboard(client,headers,db):
    auth = headers(3)
    with db.begin() as session:
        session.execute(text("UPDATE tickets SET requester_id=1 WHERE requester_id=3"))
    summary = client.get("/dashboard/summary",headers=auth).json()
    assert summary["total_tickets"] == 0 and summary["open_tickets"] == 0
    assert summary["tickets_by_status"] == []
