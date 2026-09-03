-- Parameters:
-- $1 text[] capabilities
-- $2 text worker id
-- $3 uuid lease token
-- $4 interval lease duration
WITH candidate AS (
  SELECT id
  FROM federation_jobs
  WHERE state='pending'
    AND available_at <= now()
    AND capability = ANY($1::text[])
  ORDER BY priority DESC, available_at ASC, created_at ASC
  FOR UPDATE SKIP LOCKED
  LIMIT 1
)
UPDATE federation_jobs j
SET state='running',
    attempts=j.attempts+1,
    lease_worker=$2,
    lease_token=$3,
    lease_heartbeat_at=now(),
    lease_expires_at=now() + $4::interval
FROM candidate c
WHERE j.id=c.id
RETURNING j.*;
