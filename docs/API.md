# API Guide

Base URL in development: `http://127.0.0.1:8000`. Interactive OpenAPI documentation is at `/docs`.

Except login, root, health and OpenAPI documentation, routes require `Authorization: Bearer <token>`. Protected operations use the current database user/role, never client-supplied requester or actor IDs.

## Authentication

`POST /auth/login`: form-encoded `username` (email) and `password`. Returns `access_token`, `token_type: bearer`, and safe `user` with `user_id`, `full_name`, `email`, `role`. Invalid credentials, including unset seed passwords, return 401.

`GET /auth/me`: returns `{"user": {...}}`; its role field is `role_name`, preserving the existing API.

## Tickets

| Method / path | Permission | Response |
| --- | --- | --- |
| GET /tickets/ | Authenticated; scoped | count, tickets |
| GET /tickets/{id} | Ticket access | ticket |
| POST /tickets/ | Authenticated | message, ticket |
| POST /tickets/{id}/assign | Admin | message, ticket |
| PUT /tickets/{id}/status | Admin or assigned technician | message, ticket |
| GET /tickets/{id}/comments | Ticket access | ticket_id, count, comments |
| POST /tickets/{id}/comments | Ticket access | message, comment_id, ticket_id |
| GET /tickets/{id}/history | Ticket access | ticket_id, count, history |

Creation body:

```json
{
  "title": "Lab computer cannot start",
  "description": "The workstation in the classroom will not power on.",
  "category": "Hardware",
  "priority": "HIGH",
  "department_id": 2,
  "asset_id": 1
}
```

Reference IDs must exist in your installation. An asset must belong to the specified department. If the department is omitted, its value is inferred from the asset. Both references may be null.

- Title: 3–150 characters; description: 5–2000.
- Categories: Hardware, Software, Network, Access, Other.
- Priorities: LOW, MEDIUM (default), HIGH, CRITICAL.
- String values are trimmed. Unexpected body properties are rejected.
- Requester ID comes from the JWT identity.

Assignment body: `{"technician_id": 1}`. ID is a technician profile ID, not a user ID. The profile must reference a current TECHNICIAN user and be available.

Status body: `{"new_status": "RESOLVED"}`. See the documented [workflow](ARCHITECTURE.md#ticket-lifecycle). Same-status updates return success without an extra history row.

Comment body: `{"comment_text": "Please check the power supply."}`. Trimmed length 2–1000. Actor identity comes from the authenticated user.

## Dashboard

`GET /dashboard/summary` returns total/open/in_progress/resolved/closed/high_priority/unassigned counts using keys such as `total_tickets` and `in_progress_tickets`, plus `tickets_by_status`, `tickets_by_category` and a human-readable `scope`.

High priority includes HIGH and CRITICAL. Unassigned means no current assignment row. Every count/distribution uses the same visibility predicate as the ticket list. Empty scopes return zero counts and empty distributions.

## Assets and reference data

| Path | Response |
| --- | --- |
| GET /assets/ | count, assets including tag/type/status/department |
| GET /assets/{id} | asset, count, tickets visible to this user |
| GET /lookups/departments | count, departments |
| GET /lookups/assets | count, assets with asset ID/name/department ID |
| GET /technicians/ | count, technicians with profile ID/name/email/specialization/availability |

Inventory is read-only. Asset responses do not expose assigned-user identity. Ticket details linked through an asset cannot bypass ticket authorization.

## Health and errors

`GET /` and `GET /health` are public liveness endpoints. `GET /db-health` is Admin-only and returns connection status/database name.

| Code | Meaning |
| --- | --- |
| 200 | Success, preserving existing API behavior for creation/mutations |
| 401 | Missing, invalid or expired authentication / invalid login |
| 403 | Role does not permit the operation |
| 404 | Resource missing or ticket inaccessible; technician profile invalid |
| 409 | Illegal ticket status transition |
| 422 | Invalid body, unknown fields, nonexistent department/asset or mismatch |
| 400 | Selected technician is unavailable |
| 503 | Database failure; no SQL or private parameters returned |

Errors use FastAPI's `detail` envelope (a string or validation-error list). Successful resource operations retain their existing named envelopes. Lists are currently unpaginated; React filtering operates on the already authorized list.
