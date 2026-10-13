# Security Design

## Password hashing

Passwords are hashed using pwdlib's recommended Argon2 implementation. Plaintext passwords are never persisted or returned. The password utility prompts with getpass, requires confirmation and at least eight characters, and commits only the new hash. Existing seed placeholders fail login safely instead of causing a server error.

The login API returns the same invalid-credentials message for unknown users and incorrect passwords. Password hashes never appear in identity, ticket or asset responses.

## JWT handling

Tokens are signed using the configured HS256/HS384/HS512 algorithm. Configuration fails if the secret is missing/shorter than 32 bytes, the algorithm is unsupported, or lifetime is nonpositive.

Decoding pins the algorithm and requires subject and expiry claims. Expired, malformed, tampered and deleted-user tokens are rejected. Token creation protects subject/expiry from additional-claim overrides.

Every request loads current user identity and role from the database; a stale token claiming ADMIN cannot preserve removed privileges.

## RBAC and resource authorization

Admin assignment and Admin/Technician workflow roles are checked server-side. Resource-level ticket access is checked separately:

- Admin: global visibility.
- Technician: currently assigned tickets only.
- Student/Staff: own requester ID only.

The shared scope covers lists, details, comments, history, dashboard aggregations, asset-linked tickets and updates. Inaccessible IDs return 404, matching missing IDs. Unknown roles fail closed. Request bodies cannot override requester/actor identity or include unsupported fields.

Authenticated users may browse campus asset metadata, departments and the technician directory. The directory includes technician email addresses as authenticated reference data. Asset inventory responses omit assigned-user identity. Admin-only database health avoids exposing the database name publicly.

## SQL and transaction safety

All user-supplied values use SQLAlchemy bound parameters. SQL interpolation is limited to fixed internal predicates, fixed aggregation fields and an internal locking suffix. It never interpolates client values into SQL.

Pydantic validates types, allowed values and trimmed lengths. Foreign-key existence and department/asset compatibility are checked before insertion. Workflow transitions are explicit.

A per-request session rolls back on exceptions and closes in all cases. MySQL row locks serialize assignment/status updates. The fresh database also enforces one current assignment per ticket. Database exceptions return a generic 503 and logs include only the exception class, avoiding SQL parameters and private contents.

## Secrets and configuration

Actual configuration belongs in ignored local `.env` files or deployment environment variables. `backend/.env.example` has empty secrets and supports DATABASE_URL or separate DB fields. `frontend/.env.example` contains only a public API URL.

Never put passwords, JWT secrets or private API keys in Vite variables: they are bundled into browser code. Environment files, virtual environments, node_modules, build output, caches and local tooling files are ignored.

CORS allows only configured frontend origins. CORS is not an authorization control; every protected API route independently authenticates and checks permissions.

## Known limitations

- JWTs remain valid until expiration unless user access/roles change or the signing key rotates. There is no refresh-token or individual token revocation system.
- Browser tokens use localStorage to preserve the existing flow; XSS could steal them. React escapes rendered text, but production hardening should consider secure HttpOnly cookies, CSP and an appropriate CSRF design.
- There is no login throttling, MFA, password reset, self-service registration or account lockout.
- Password setup is a local administrative command, not a public account-management API.
- HTTPS, reverse proxy security, production log management and monitoring require deployment configuration.
- The database account must be configured with appropriate least privileges.
- Reassignment updates the current assignment; full assignment audit history is future work.
- Legacy databases need duplicate review before adding the optional unique assignment constraint.
- Authorization tests and browser smoke tests are meaningful regressions, not a formal penetration test or production security certification.

No real credentials or working public demo passwords are distributed with the repository.
