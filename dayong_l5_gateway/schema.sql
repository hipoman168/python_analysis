-- DAYONG L5 durable message schema v0.2; provision on non-expiring PostgreSQL.
CREATE TABLE IF NOT EXISTS l5_agents (
 agent_id TEXT PRIMARY KEY,
 center_id TEXT NOT NULL,
 active BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS l5_messages (
 message_id UUID PRIMARY KEY,
 correlation_id UUID NOT NULL,
 task_id TEXT NOT NULL,
 task_version INTEGER NOT NULL DEFAULT 1,
 sender_agent_id TEXT NOT NULL REFERENCES l5_agents(agent_id),
 recipient_agent_id TEXT NOT NULL REFERENCES l5_agents(agent_id),
 payload JSONB NOT NULL,
 required_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
 evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
 status TEXT NOT NULL DEFAULT 'SENT' CHECK(status IN ('SENT','ACK_ACCEPTED','ACK_REJECTED','REPLIED','DELIVERY_CONFIRMED','FAILED')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 ack_at TIMESTAMPTZ,
 replied_at TIMESTAMPTZ,
 confirmed_at TIMESTAMPTZ,
 expires_at TIMESTAMPTZ,
 reply_payload JSONB,
 UNIQUE(message_id,recipient_agent_id)
);
CREATE INDEX IF NOT EXISTS idx_l5_inbox ON l5_messages(recipient_agent_id,status,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_l5_correlation ON l5_messages(correlation_id);
CREATE TABLE IF NOT EXISTS l5_events (
 event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 message_id UUID NOT NULL REFERENCES l5_messages(message_id),
 actor_agent_id TEXT NOT NULL REFERENCES l5_agents(agent_id),
 event_type TEXT NOT NULL,
 event_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_l5_events_message ON l5_events(message_id,created_at);
