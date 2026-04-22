-- OSLO POC Additions — wearable_reading + smart_report_cache
-- Migration 002

CREATE TABLE IF NOT EXISTS wearable_reading (
  reading_id BIGSERIAL PRIMARY KEY,
  owner_id UUID NOT NULL,
  profile_id UUID NOT NULL REFERENCES profile(profile_id),
  metric TEXT NOT NULL,  -- 'resting_hr' | 'hrv' | 'sleep_minutes' | 'steps'
  value NUMERIC NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL,
  source TEXT NOT NULL DEFAULT 'health_connect',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_wearable_profile_metric
  ON wearable_reading(profile_id, metric, observed_at DESC);

CREATE TABLE IF NOT EXISTS smart_report_cache (
  report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_id UUID NOT NULL,
  profile_id UUID NOT NULL REFERENCES profile(profile_id),
  report_type TEXT NOT NULL,  -- 'smart_report' | 'timeline_summary'
  content_markdown TEXT NOT NULL,
  source_document_ids UUID[],
  generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + interval '24 hours'),
  sections JSONB,
  model_version TEXT
);
CREATE INDEX IF NOT EXISTS idx_smart_report_profile
  ON smart_report_cache(profile_id, report_type, generated_at DESC);

-- Add processing_status to document for async classify+extract pipeline
ALTER TABLE document ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT 'pending';
-- 'pending' | 'classifying' | 'extracting' | 'complete' | 'failed'

-- Add explanation cache to extraction
ALTER TABLE extraction ADD COLUMN IF NOT EXISTS explanation_markdown TEXT;
ALTER TABLE extraction ADD COLUMN IF NOT EXISTS explanation_generated_at TIMESTAMPTZ;

-- Enable RLS on new tables
ALTER TABLE wearable_reading ENABLE ROW LEVEL SECURITY;
ALTER TABLE smart_report_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_wearable ON wearable_reading
  USING (owner_id = current_setting('oslo.current_owner_id')::uuid);
CREATE POLICY tenant_smart_report ON smart_report_cache
  USING (owner_id = current_setting('oslo.current_owner_id')::uuid);
