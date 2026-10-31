-- DIRECTIVE 131 / HOTFIX-A: Atomic Idempotency Table Schema
-- Purpose: Guarantees exactly-once atomic execution for all vehicle/photo/status synchronization mutations.
-- D1 Remote & Local Engine Compatibility

CREATE TABLE IF NOT EXISTS sync_idempotency_keys (
  idempotency_key TEXT PRIMARY KEY,
  endpoint TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  status TEXT NOT NULL, -- 'IN_PROGRESS', 'COMPLETED', 'FAILED'
  response_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sync_idempotency_endpoint ON sync_idempotency_keys(endpoint);
CREATE INDEX IF NOT EXISTS idx_sync_idempotency_status ON sync_idempotency_keys(status);
