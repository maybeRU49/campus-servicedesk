# Database Design

## Schema and initialization

`backend/sql/schema.sql` targets MySQL 8 and creates nine tables plus `vw_ticket_details`. `seed.sql` is for an empty demo installation only. It inserts four roles, six departments, four users, one technician, two assets and three sample tickets. Password placeholders cannot authenticate; set passwords with the interactive utility.

Initial SQL uses the database name `campus_servicedesk`. Configuration must select the same database, or scripts must be adapted deliberately for a different installation. Index and seed statements are not safe to rerun indiscriminately.

## Tables and keys

| Table | Primary key | Important relationships / purpose |
| --- | --- | --- |
| roles | role_id | Unique role_name |
| departments | department_id | Unique department_name |
| users | user_id | Unique email; role and optional department |
| assets | asset_id | Unique asset_tag; type/status; optional department and assigned user |
| technicians | technician_id | Unique user_id; specialization and availability |
| tickets | ticket_id | Requester; optional department and asset; category/priority/status/timestamps |
| ticket_assignments | assignment_id | Ticket + technician profile; current assignment |
| ticket_comments | comment_id | Ticket + author; text/timestamp |
| ticket_status_history | history_id | Ticket + actor; old/new status/timestamp |

The schema uses foreign keys to prevent orphan references. The API checks department/asset compatibility and technician roles because simple foreign keys cannot express those business rules. Status/category/priority values are validated by Pydantic and workflow helpers; the original database stores them as VARCHAR rather than MySQL ENUM.

## Joins and the view

`vw_ticket_details` INNER JOINs the requester and LEFT JOINs optional department, asset, assignment, technician and technician user data. LEFT JOINs preserve tickets without assets or assignments.

Detailed reads join the view back to `tickets` for description. Scoped list/detail queries operate on underlying requester IDs and assignment/profile relationships. The technician predicate uses EXISTS so visibility is based on a matching assignment rather than a display name.

Asset detail queries join the same view but include both asset ID and ticket visibility. Dashboard SQL aggregates directly over scoped tickets rather than aggregating an unrestricted view.

## Indexes

Explicit indexes cover ticket status, priority, category, created time, department and assigned technician. Primary/unique keys and MySQL foreign-key indexes support ID lookups, joins, requester scoping and assignment existence checks.

The fresh schema adds a unique ticket key on `ticket_assignments`, reflecting the original API's single current assignment model. Reassignment updates that row; this table is not a full assignment audit log.

## Existing installation migration

The authorization fix itself needs no database reset or migration.

For the additional assignment constraint:

1. Back up the existing database.
2. Review `backend/sql/migrate_assignment_uniqueness.sql`.
3. Run its duplicate-detection SELECT separately. It must return no rows.
4. If duplicates exist, stop and inspect them. The project never deletes or merges them automatically.
5. Run the ALTER TABLE once to add `uq_assignments_ticket`.

The ALTER fails if duplicate ticket assignments exist, preserving those records. Do not reapply the constraint if it already exists. Existing duplicate assignments can duplicate rows in the original view until manually reconciled. Application mutations serialize through a parent-ticket lock; database uniqueness provides additional protection against out-of-band writes.

No schema/seed scripts were run against the original project database during this improvement. MySQL integration and browser verification used a separate newly created test database.

## Transactions and concurrency

Creation inserts the ticket and initial history before one commit. Assignment plus automatic progress/history is atomic. Status updates and their history share one commit. Comments store the authenticated author.

MySQL FOR UPDATE locks the parent ticket for assignment/status changes until commit or rollback. Subsequent requests through the API read the serialized current state. All request exceptions trigger rollback and session closure; database errors are sanitized at the HTTP boundary.

The rollback regression test forces history insertion to fail after a status UPDATE and verifies that both the status change and history are rolled back.

## Testing portability

Default tests adapt the actual MySQL schema to SQLite: identity columns, ON UPDATE syntax and view replacement are adjusted, and foreign keys are enabled. This gives quick isolated authorization/workflow coverage. A separate MySQL suite verifies the original DDL, real view/joins, aggregation and MySQL locking query path. These tests do not constitute a concurrency/load benchmark.
