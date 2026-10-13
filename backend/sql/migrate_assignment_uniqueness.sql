-- Optional, additive migration for an EXISTING database. Run once, after backup.
-- First query must return no rows. If duplicates exist, STOP and review them;
-- never delete historical data automatically to make this migration pass.
SELECT ticket_id, COUNT(*) AS assignments
FROM ticket_assignments GROUP BY ticket_id HAVING COUNT(*) > 1;

-- Fails safely with a duplicate-key error if the preflight found duplicate rows.
ALTER TABLE ticket_assignments
ADD CONSTRAINT uq_assignments_ticket UNIQUE (ticket_id);
