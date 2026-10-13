# Campus ServiceDesk & Asset Management System

A full-stack campus IT support application built with **FastAPI, React and MySQL**. Users submit support requests, administrators assign technicians, and technicians track work through resolution. Ticket visibility is enforced by the API for every role.

## Overview

This project demonstrates practical REST API development, relational SQL, JWT authentication, server-side authorization and frontend integration. It extends the original application and Git history with scoped access, validation, asset browsing, automated tests and documentation.

## Key Features

- JWT login, Argon2 password hashing, persistent login and session-expiry handling.
- Role-scoped ticket lists, details, dashboard counts, comments and status history.
- Tickets with category, priority, department and optional campus asset.
- Admin technician assignment/reassignment; scoped technician workflow updates.
- Atomic status changes and audit history, including initial creation for new tickets.
- Read-only asset inventory with type, status, department and permitted linked tickets.
- Responsive UI with search, status/priority filters, loading feedback and empty/error states.
- Parameterized SQL, validated foreign keys and transaction rollback.

## Architecture

```text
React / Vite
    |
    | REST / JSON + Bearer JWT
    v
FastAPI -- authentication + role/data authorization
    |
    | SQLAlchemy sessions + parameterized SQL
    v
MySQL -- foreign keys, indexes, joins, ticket detail view
```

SQLAlchemy manages database connections and transactions. The application uses readable SQL rather than ORM entity models. See [architecture](docs/ARCHITECTURE.md).

## Technology Stack

| Layer | Technologies |
| --- | --- |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, PyMySQL |
| Security | PyJWT, pwdlib / Argon2 |
| Frontend | React, JavaScript, Vite, CSS, Fetch API |
| Database | MySQL 8, relational SQL, views, indexes, foreign keys |
| Quality | pytest, FastAPI TestClient, Node test runner, ESLint, Git |

## Role Model

| Role | Ticket visibility / dashboard | Workflow permissions |
| --- | --- | --- |
| ADMIN | All campus tickets | Create, comment, assign/reassign, update status, reopen closed tickets |
| TECHNICIAN | Tickets currently assigned to their technician profile | Create requests, comment and update assigned tickets |
| STAFF | Their own requests | Create, view and comment |
| STUDENT | Their own requests | Create, view and comment |

Technicians do not have an unassigned queue and cannot assign themselves work. A request created by a technician becomes visible in their work queue only when assigned to them. Campus asset metadata and lookup data are shared with authenticated users; asset-linked tickets always obey ticket visibility.

## Ticket Workflow

```text
OPEN -> IN_PROGRESS -> RESOLVED -> CLOSED
           |             |
           v             v
          OPEN       IN_PROGRESS

CLOSED -> OPEN (Admin only)
```

Assigning an OPEN ticket moves it to IN_PROGRESS in the same transaction. Reassignment changes the current technician without inventing a status change. Repeating the same status is a no-op; unsupported transitions return 409. Resolution timestamps are retained when closing and cleared when reopening. Every actual status change records its actor and timestamp. Older tickets retain their original history; no historical events are fabricated.

## Database Design

Nine tables model roles, users, departments, assets, technicians, tickets, current assignments, comments and status history. Users request tickets; optional department/asset relationships add context. Technician profiles reference users, and assignments reference profiles. Comments and history retain the authenticated actor.

The `vw_ticket_details` view joins requester, department, asset and technician names. Authorization is applied against underlying ticket/user IDs, never display names. See [database design and migration notes](docs/DATABASE.md).

## API Overview

| Endpoint | Purpose |
| --- | --- |
| POST /auth/login; GET /auth/me | Login / authenticated identity |
| GET, POST /tickets/ | Scoped ticket list / creation |
| GET /tickets/{id} | Permitted ticket details |
| POST /tickets/{id}/assign | Admin assignment/reassignment |
| PUT /tickets/{id}/status | Permitted workflow update |
| GET, POST /tickets/{id}/comments | Permitted comment reads/writes |
| GET /tickets/{id}/history | Permitted status history |
| GET /dashboard/summary | Role-scoped statistics |
| GET /lookups/departments; GET /lookups/assets | Ticket form reference data |
| GET /technicians/ | Authenticated technician directory |
| GET /assets/; GET /assets/{id} | Inventory / asset and visible linked tickets |

Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). See [API guide](docs/API.md) for bodies and errors.

## Installation

Prerequisites: **Python 3.10+**, **Node.js 20.19+ or 22.12+**, **MySQL 8**, Git, and npm. The commands below use PowerShell. Substitute your Python launcher if `py` is unavailable.

### 1. Clone and install backend dependencies

```powershell
git clone https://github.com/maybeRU49/campus-servicedesk.git
cd campus-servicedesk
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
Copy-Item backend\.env.example backend\.env
```

Set either `DATABASE_URL=mysql+pymysql://...` or the separate `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` values in `backend/.env`. A URL takes precedence; percent-encode special characters in URL credentials. Prefer a dedicated application database account.

Generate a unique JWT secret and put the result in the local `JWT_SECRET_KEY` setting:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

JWT secrets must contain at least 32 bytes. Supported algorithms are HS256, HS384 and HS512. `CORS_ORIGINS` is a comma-separated frontend allowlist.

### 2. Initialize a NEW MySQL database

Open MySQL Workbench, connect to your server, then execute these files in order:

1. `backend/sql/schema.sql`
2. `backend/sql/seed.sql`

Alternatively, in the MySQL command-line client:

```sql
SOURCE C:/path/to/campus-servicedesk/backend/sql/schema.sql;
SOURCE C:/path/to/campus-servicedesk/backend/sql/seed.sql;
```

These scripts create/use `campus_servicedesk`. Keep `DB_NAME` consistent. **Do not rerun seed/schema scripts on an existing populated database**: seeds are initial demo data, and index creation is not a migration system.

For an existing installation, preserve its database and configuration. Review the optional additive assignment constraint migration in [DATABASE.md](docs/DATABASE.md); no data deletion or reset is needed for the authorization fix.

Seed users have deliberately unusable `dummy_hash` passwords. Set your own passwords interactively from the backend folder:

```powershell
cd backend
..\.venv\Scripts\python.exe -m scripts.set_password admin@example.com
..\.venv\Scripts\python.exe -m scripts.set_password tech1@example.com
..\.venv\Scripts\python.exe -m scripts.set_password rohan@example.com
..\.venv\Scripts\python.exe -m scripts.set_password staff@example.com
```

There are no published working demo credentials and no self-registration endpoint.

### 3. Start the backend

From `backend/`:

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Check `/health` and `/docs`. Database connectivity is checked separately by the Admin-only `/db-health` endpoint.

### 4. Start the frontend in a second terminal

From the repository root:

```powershell
cd frontend
Copy-Item .env.example .env
npm ci
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). `VITE_API_URL` defaults to `http://127.0.0.1:8000`; restart Vite after changing environment values. Only public configuration belongs in Vite environment variables.

## Authentication

Login submits form fields `username` (email) and `password`. The backend verifies the password hash and returns a signed, expiring bearer JWT plus safe user identity. React sends the token in the Authorization header and checks `/auth/me` when restoring a session. Logout clears local state and token storage; expired tokens return the user to login.

## Authorization

The API loads the user's current database role on every request. A shared access helper scopes ticket reads and mutations by requester ID or assigned technician user ID. This policy covers comments, history, dashboards and asset-linked tickets. Inaccessible and nonexistent tickets both return 404. Workflow roles are checked before mutation; assignment remains Admin-only. React controls improve usability; they do not grant access.

See [security design and limitations](docs/SECURITY.md).

## Screenshots

Actual browser captures from a separate MySQL test database with synthetic accounts; these are not design mockups.

| Admin dashboard | Ticket workflow |
| --- | --- |
| ![Admin dashboard](docs/screenshots/admin-dashboard.png) | ![Assignment, comments and history](docs/screenshots/ticket-workflow.png) |

[Student dashboard](docs/screenshots/student-dashboard.png) · [Asset details](docs/screenshots/asset-details.png) · [Mobile layout](docs/screenshots/mobile-student.png)

## Testing

From `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
```

The default suite uses a fresh SQLite in-memory database adapted from the MySQL schema, including real foreign keys and the ticket view. It never connects to the local application database.

For MySQL integration testing, first create an **empty dedicated** database named `campus_servicedesk_test_<suffix>`, then set its connection URL:

```powershell
$env:TEST_DATABASE_URL = "mysql+pymysql://test_user:YOUR_PASSWORD@127.0.0.1:3306/campus_servicedesk_test_local"
..\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:TEST_DATABASE_URL
```

The tests refuse other MySQL database names. They initialize the schema and replace synthetic fixtures in that test database. Never use an application database for tests.

From `frontend/`:

```powershell
npm test
npm run lint
npm run build
```

Verified: **87 backend cases on SQLite and MySQL, 6 frontend request tests**, frontend lint/build and browser smoke flows for all four roles. See [verification report](docs/TESTING.md).

## Project Structure

```text
backend/
  app/
    access.py             shared ticket data scoping
    database.py           engine and transactional sessions
    security.py           hashing, JWT and role dependencies
    schemas.py            validated request bodies
    workflow.py           references, transitions and history
    main.py               API, CORS and safe database errors
    routers/              auth, tickets, dashboard, assets and lookups
  scripts/set_password.py interactive local password setup
  sql/                    schema, initial seeds and additive migration
  tests/                  isolated API regression tests
  .env.example
  requirements.txt
  requirements-dev.txt
frontend/
  src/
    App.jsx               existing screens and interactions
    api.js                shared authenticated requests/error handling
    api.test.js
    components/           dashboard and asset browser
    App.css
    index.css
  .env.example
docs/
  ARCHITECTURE.md
  API.md
  DATABASE.md
  SECURITY.md
  TESTING.md
  screenshots/
```

## Future Improvements

- SLA targets and breach tracking.
- Email/in-app notifications and attachments.
- Server-side pagination and reporting for larger datasets.
- Asset lifecycle editing and assignment audit history.
- Production deployment with HTTPS, rate limiting, monitoring and token revocation.

This is a portfolio application, not a complete production ITSM platform.
