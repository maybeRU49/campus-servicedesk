# Verification Report

Verified on 13 October 2026 with Python 3.10, MySQL 8, the installed Node/Vite toolchain and a real headless Microsoft Edge browser.

## Automated checks

| Check | Result |
| --- | --- |
| Backend pytest, isolated SQLite | 87 passed |
| Same backend suite, separate MySQL database | 87 passed |
| Frontend Node request tests | 6 passed |
| ESLint | Passed |
| Vite production build | Passed |

The current Starlette release emits one deprecation warning for its httpx TestClient integration. Tests pass; migration to its suggested test client dependency can be evaluated separately.

Backend tests cover valid/invalid login, seed password placeholders, authenticated identity, missing/tampered/expired tokens, missing required claims, current-role enforcement, all protected read/write routes, Admin visibility, two requesters per role, two technicians, guessed IDs, scoped dashboard distributions, asset-linked ticket isolation, creation, validation, comments, assignment/reassignment, status transitions, initial/history actor records, empty scopes and rollback.

Frontend request tests cover validation error formatting, bearer/JSON requests, expired sessions, invalid login, rejection of responses from an old account, network errors and non-JSON server failures.

## Browser and direct API smoke verification

Browser interactions used synthetic users in a newly created, isolated MySQL test database. No existing application's passwords were changed and no existing ticket data was modified.

| Role | Verified interactions |
| --- | --- |
| Admin | Login; all tickets/global dashboard; create; assign and reassign between two technicians; status updates; comment; inventory/detail browsing |
| Technician | Login; assigned queue; allowed detail/status/comment; assignment controls absent; direct assignment 403; other technician's ticket 404 |
| Student | Login; create; own list/detail/comment/dashboard; direct foreign ticket/comments/history 404; own status/assignment 403 |
| Staff | Same requester isolation checks as Student |

Additional browser checks: login persistence after reload, search/empty states, department-filtered asset options, session-expiry logout, 390px mobile layout without horizontal overflow, and no uncaught browser exceptions.

The direct ID security check used the logged-in Student JWT to request an Admin-created ticket: the backend returned 404. Staff was verified the same way. Dashboard totals were compared with authorized ticket list counts.

## Data safety and scope

The original baseline contained seven tickets; before the fix a Student could retrieve all seven and an anonymous dashboard request returned 200. After the authorization fix, read-only checks against that database returned Admin 7, Technician 5, Student 2 and Staff 1; each dashboard matched. Student access to another user's ID returned 404 and anonymous dashboard access returned 401.

Mutation/regression/browser testing used synthetic fixtures only. The default automated suite is in-memory SQLite. MySQL testing requires a database name starting with `campus_servicedesk_test_`, and replaces fixtures only inside that isolated database.

## Running checks

See the [README testing instructions](../README.md#testing). Backend tests use the application routers and real SQL rather than mocking authorization results. MySQL coverage exercises real DDL, views, joins and transaction behavior. Browser captures in [screenshots](screenshots/README.md) document actual observed UI states.

Future coverage can add concurrent-update stress tests, automated accessibility auditing and a packaged browser regression suite. Current browser smoke verification is documented, not installed as a required frontend test dependency.
