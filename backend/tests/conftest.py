"""Isolated fixtures: never connect to the developer's application database."""
import os
import re
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set before importing the application. Existing .env values cannot override these.
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "sqlite://")
os.environ["JWT_SECRET_KEY"] = "test-only-secret-with-at-least-32-bytes"
os.environ["JWT_ALGORITHM"] = "HS256"

from app.database import get_db
from app.main import app
from app.security import hash_password
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def test_engine():
    url = make_url(os.environ["DATABASE_URL"])
    if url.get_backend_name() != "sqlite":
        if not (url.database or "").startswith("campus_servicedesk_test_"):
            raise RuntimeError("MySQL tests require a dedicated campus_servicedesk_test_* database")
        engine = create_engine(url, pool_pre_ping=True)
    else:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                               poolclass=StaticPool)
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
    schema = (Path(__file__).parents[1] / "sql" / "schema.sql").read_text(encoding="utf-8-sig")
    with engine.begin() as conn:
        for statement in schema.split(";"):
            statement = statement.strip()
            if not statement or statement.startswith(("CREATE DATABASE", "USE ")):
                continue
            if engine.dialect.name == "sqlite":
                statement = statement.replace("INT AUTO_INCREMENT PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
                statement = statement.replace(" ON UPDATE CURRENT_TIMESTAMP", "")
                statement = statement.replace("CREATE OR REPLACE VIEW", "CREATE VIEW")
            if statement.startswith("CREATE INDEX") and engine.dialect.name == "mysql":
                index_name = re.search(r"CREATE INDEX (\w+)", statement).group(1)
                exists = conn.execute(text("""
                    SELECT COUNT(*) FROM information_schema.statistics
                    WHERE table_schema = DATABASE() AND index_name = :name
                """), {"name": index_name}).scalar()
                if exists:
                    continue
            conn.execute(text(statement))
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def encoded_password():
    return hash_password("test-password-123")


@pytest.fixture()
def db(test_engine, encoded_password):
    # Only synthetic fixtures in the guarded test database are removed.
    with test_engine.begin() as conn:
        for table in ["ticket_status_history", "ticket_comments", "ticket_assignments",
                      "tickets", "technicians", "assets", "users", "departments", "roles"]:
            conn.execute(text(f"DELETE FROM {table}"))
        for id_, role in enumerate(["ADMIN", "TECHNICIAN", "STUDENT", "STAFF"], 1):
            conn.execute(text("INSERT INTO roles (role_id,role_name) VALUES (:id,:role)"),
                         {"id": id_, "role": role})
        conn.execute(text("INSERT INTO departments VALUES (1,'IT Services'),(2,'CSE')"))
        # Two users of every non-admin role detect accidental role-wide access.
        for id_, role_id in [(1,1),(2,2),(3,3),(4,4),(5,2),(6,3),(7,4)]:
            conn.execute(text("""
                INSERT INTO users (user_id, full_name, email, password_hash, role_id, department_id)
                VALUES (:id, :name, :email, :password, :role, 1)
            """), {"id": id_, "name": f"User {id_}", "email": f"user{id_}@example.com",
                   "password": encoded_password, "role": role_id})
        conn.execute(text("""
            INSERT INTO technicians (technician_id,user_id,is_available)
            VALUES (1,2,1),(2,5,1)
        """))
        conn.execute(text("""
            INSERT INTO assets (asset_id,asset_tag,asset_name,asset_type,department_id)
            VALUES (1,'IT-PC-1','Lab PC','Computer',1),(2,'CSE-PR-1','Printer','Printer',2)
        """))
        for id_, requester in [(1,1),(2,3),(3,4),(4,6),(5,7)]:
            conn.execute(text("""
                INSERT INTO tickets (ticket_id,title,description,category,priority,status,requester_id,department_id,asset_id)
                VALUES (:id,:title,'A useful description','Hardware','HIGH','OPEN',:requester,1,1)
            """), {"id": id_, "title": f"Ticket {id_}", "requester": requester})
        conn.execute(text("INSERT INTO ticket_assignments (ticket_id,technician_id) VALUES (2,1),(3,2)"))
    factory = sessionmaker(bind=test_engine)
    yield factory


@pytest.fixture()
def client(db):
    def override_db():
        session = db()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture()
def headers(client):
    def for_user(user_id):
        result = client.post("/auth/login", data={
            "username": f"user{user_id}@example.com", "password": "test-password-123"
        })
        assert result.status_code == 200
        return {"Authorization": "Bearer " + result.json()["access_token"]}
    return for_user
