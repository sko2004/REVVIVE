-- Do-It agent: durable run history + tool trace (PostgreSQL)
-- Canonical DDL is inlined in postgres_db.py (_DDL_STATEMENTS); this file is for manual psql / docs.
-- psql "$DATABASE_URL" -f db/schema.sql

CREATE TABLE IF NOT EXISTS agent_runs (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_message TEXT NOT NULL,
    assistant_final TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS agent_steps (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES agent_runs (id) ON DELETE CASCADE,
    step_no INT NOT NULL,
    kind TEXT NOT NULL,
    tool_name TEXT,
    tool_call_id TEXT,
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, step_no)
);

CREATE INDEX IF NOT EXISTS idx_agent_steps_run ON agent_steps (run_id, step_no);

-- Human-in-the-loop: irreversible deletes are queued here until approved in the UI
CREATE TABLE IF NOT EXISTS pending_actions (
    id UUID PRIMARY KEY,
    run_id UUID REFERENCES agent_runs (id) ON DELETE SET NULL,
    task_id TEXT NOT NULL,
    task_title TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    resolution_note TEXT
);

ALTER TABLE pending_actions
    ADD COLUMN IF NOT EXISTS action_type TEXT DEFAULT 'delete',
    ADD COLUMN IF NOT EXISTS action_detail JSONB NOT NULL DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_pending_open ON pending_actions (status) WHERE status = 'pending';

CREATE TABLE IF NOT EXISTS pricing_history (
    id SERIAL PRIMARY KEY,
    subsystem TEXT NOT NULL,
    symptom_category TEXT,
    vehicle_category TEXT,
    region TEXT,
    cost_min NUMERIC,
    cost_max NUMERIC,
    sample_size INT,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bookings (
    id TEXT PRIMARY KEY,
    run_id UUID REFERENCES agent_runs(id),
    owner_id TEXT,
    provider_id TEXT,
    provider_name TEXT,
    issue_summary TEXT,
    triage_json JSONB,
    estimated_cost_min NUMERIC,
    estimated_cost_max NUMERIC,
    urgency TEXT,
    status TEXT DEFAULT 'confirmed',
    booked_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
