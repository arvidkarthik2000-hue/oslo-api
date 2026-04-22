-- OSLO Initial Schema — Postgres 16 + pgvector
-- Run via Alembic or directly on fresh database

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- OWNERS
CREATE TABLE owner (
  owner_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  phone_number TEXT NOT NULL UNIQUE,
  phone_verified_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  subscription_tier TEXT NOT NULL DEFAULT 'free',
  subscription_expires_at TIMESTAMPTZ,
  razorpay_customer_id TEXT,
  kms_key_arn TEXT,
  deleted_at TIMESTAMPTZ
);

-- PROFILES
CREATE TABLE profile (
  profile_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_id UUID NOT NULL REFERENCES owner(owner_id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  relationship TEXT NOT NULL,
  dob DATE,
  sex TEXT,
  blood_group TEXT,
  pregnancy_status TEXT,
  avatar_color TEXT,
  abha_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ,
  CONSTRAINT one_self_per_owner UNIQUE (owner_id, relationship) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX idx_profile_owner ON profile(owner_id);

-- DOCUMENTS
CREATE TABLE document (
  document_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_id UUID NOT NULL REFERENCES owner(owner_id),
  profile_id UUID NOT NULL REFERENCES profile(profile_id),
  source TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  byte_size INTEGER NOT NULL,
  page_count INTEGER NOT NULL DEFAULT 1,
  s3_key TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  classified_as TEXT,
  classification_confidence REAL,
  classification_model_version TEXT,
  document_date DATE,
  provider_name TEXT,
  deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_document_owner_profile ON document(owner_id, profile_id);
CREATE INDEX idx_document_date ON document(profile_id, document_date DESC NULLS LAST);
CREATE INDEX idx_document_classified ON document(profile_id, classified_as);

-- EXTRACTIONS
CREATE TABLE extraction (
  extraction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  document_id UUID NOT NULL REFERENCES document(document_id) ON DELETE CASCADE,
  owner_id UUID NOT NULL,
  profile_id UUID NOT NULL,
  model_version TEXT NOT NULL,
  schema_version TEXT NOT NULL DEFAULT 'v1',
  json_payload JSONB NOT NULL,
  validation_flags JSONB,
  validated_at TIMESTAMPTZ,
  user_corrected BOOLEAN NOT NULL DEFAULT false,
  user_corrected_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  is_current BOOLEAN NOT NULL DEFAULT true
);
CREATE INDEX idx_extraction_document ON extraction(document_id);
CREATE INDEX idx_extraction_current ON extraction(document_id) WHERE is_current;

-- LAB VALUES
CREATE TABLE lab_value (
  lab_value_id BIGSERIAL PRIMARY KEY,
  owner_id UUID NOT NULL,
  profile_id UUID NOT NULL REFERENCES profile(profile_id),
  document_id UUID NOT NULL REFERENCES document(document_id) ON DELETE CASCADE,
  extraction_id UUID NOT NULL REFERENCES extraction(extraction_id) ON DELETE CASCADE,
  test_name TEXT NOT NULL,
  loinc_code TEXT,
  value_num NUMERIC,
  value_text TEXT,
  unit TEXT,
  ref_low NUMERIC,
  ref_high NUMERIC,
  observed_at TIMESTAMPTZ NOT NULL,
  flag TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_lab_value_profile_test ON lab_value(profile_id, loinc_code, observed_at DESC);
CREATE INDEX idx_lab_value_profile_date ON lab_value(profile_id, observed_at DESC);

-- PRESCRIPTIONS
CREATE TABLE prescription (
  prescription_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_id UUID NOT NULL,
  profile_id UUID NOT NULL REFERENCES profile(profile_id),
  document_id UUID REFERENCES document(document_id),
  prescribed_by TEXT,
  prescribing_rmp_nmc TEXT,
  prescribed_at DATE NOT NULL,
  items JSONB NOT NULL,
  active BOOLEAN NOT NULL DEFAULT true,
  started_at DATE,
  ended_at DATE,
  source TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_rx_profile_active ON prescription(profile_id, active);

-- TIMELINE EVENTS
CREATE TABLE timeline_event (
  event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_id UUID NOT NULL,
  profile_id UUID NOT NULL REFERENCES profile(profile_id),
  event_type TEXT NOT NULL,
  occurred_at TIMESTAMPTZ NOT NULL,
  source_ref UUID,
  source_ref_type TEXT,
  title TEXT NOT NULL,
  subtitle TEXT,
  provider TEXT,
  flags JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_timeline_profile_date ON timeline_event(profile_id, occurred_at DESC);

-- EMERGENCY PROFILE
CREATE TABLE emergency_profile (
  profile_id UUID PRIMARY KEY REFERENCES profile(profile_id) ON DELETE CASCADE,
  allergies JSONB NOT NULL DEFAULT '[]'::jsonb,
  chronic_conditions JSONB NOT NULL DEFAULT '[]'::jsonb,
  current_medications JSONB NOT NULL DEFAULT '[]'::jsonb,
  emergency_contacts JSONB NOT NULL DEFAULT '[]'::jsonb,
  organ_donor BOOLEAN DEFAULT false,
  advance_directives TEXT,
  last_reviewed_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- CONSENTS
CREATE TABLE consent (
  consent_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_id UUID NOT NULL REFERENCES owner(owner_id),
  purpose TEXT NOT NULL,
  granted BOOLEAN NOT NULL,
  granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at TIMESTAMPTZ,
  consent_text_version TEXT NOT NULL,
  consent_text TEXT NOT NULL,
  ip_address TEXT,
  user_agent TEXT,
  scope JSONB
);
CREATE INDEX idx_consent_owner_purpose ON consent(owner_id, purpose, granted_at DESC);

-- SHARE LINKS
CREATE TABLE share_link (
  share_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_id UUID NOT NULL,
  profile_id UUID NOT NULL REFERENCES profile(profile_id),
  created_by_owner_id UUID NOT NULL REFERENCES owner(owner_id),
  doctor_name TEXT,
  doctor_nmc TEXT,
  scope JSONB NOT NULL,
  jwt_token_hash TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  accessed_at TIMESTAMPTZ[],
  revoked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- TELECONSULT SESSIONS
CREATE TABLE rmp (
  rmp_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  nmc_registration_number TEXT NOT NULL UNIQUE,
  qualification TEXT NOT NULL,
  specialty TEXT NOT NULL,
  phone TEXT NOT NULL UNIQUE,
  email TEXT,
  active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE teleconsult_session (
  session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_id UUID NOT NULL REFERENCES owner(owner_id),
  profile_id UUID NOT NULL REFERENCES profile(profile_id),
  rmp_id UUID NOT NULL,
  rmp_nmc TEXT NOT NULL,
  rmp_name TEXT NOT NULL,
  rmp_qualification TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'awaiting_response',
  patient_consent_recorded_at TIMESTAMPTZ NOT NULL,
  patient_consent_text TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  closed_at TIMESTAMPTZ,
  retention_until TIMESTAMPTZ NOT NULL
);
CREATE INDEX idx_tele_owner ON teleconsult_session(owner_id);
CREATE INDEX idx_tele_rmp ON teleconsult_session(rmp_id, status);

CREATE TABLE teleconsult_message (
  message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id UUID NOT NULL REFERENCES teleconsult_session(session_id) ON DELETE CASCADE,
  sender TEXT NOT NULL,
  content TEXT NOT NULL,
  attachments JSONB,
  emergency_trigger_detected BOOLEAN DEFAULT false,
  sent_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_tele_msg_session ON teleconsult_message(session_id, sent_at);

-- AUDIT LOG
CREATE TABLE audit_event (
  audit_id BIGSERIAL PRIMARY KEY,
  owner_id UUID,
  profile_id UUID,
  action TEXT NOT NULL,
  actor_type TEXT NOT NULL,
  actor_id UUID,
  resource_type TEXT,
  resource_id UUID,
  metadata JSONB,
  ip_address TEXT,
  user_agent TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_owner_time ON audit_event(owner_id, created_at DESC);

-- DOCUMENT EMBEDDINGS
CREATE TABLE document_embedding (
  embedding_id BIGSERIAL PRIMARY KEY,
  owner_id UUID NOT NULL,
  profile_id UUID NOT NULL,
  document_id UUID NOT NULL REFERENCES document(document_id) ON DELETE CASCADE,
  chunk_type TEXT NOT NULL,
  chunk_text TEXT NOT NULL,
  embedding vector(1024) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_embedding_owner_profile ON document_embedding(owner_id, profile_id);
CREATE INDEX idx_embedding_vec ON document_embedding USING hnsw (embedding vector_cosine_ops);

-- ROW-LEVEL SECURITY
ALTER TABLE profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE document ENABLE ROW LEVEL SECURITY;
ALTER TABLE extraction ENABLE ROW LEVEL SECURITY;
ALTER TABLE lab_value ENABLE ROW LEVEL SECURITY;
ALTER TABLE prescription ENABLE ROW LEVEL SECURITY;
ALTER TABLE timeline_event ENABLE ROW LEVEL SECURITY;
ALTER TABLE emergency_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE consent ENABLE ROW LEVEL SECURITY;
ALTER TABLE share_link ENABLE ROW LEVEL SECURITY;
ALTER TABLE teleconsult_session ENABLE ROW LEVEL SECURITY;
ALTER TABLE teleconsult_message ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_embedding ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_profile ON profile USING (owner_id = current_setting('oslo.current_owner_id')::uuid);
CREATE POLICY tenant_document ON document USING (owner_id = current_setting('oslo.current_owner_id')::uuid);
CREATE POLICY tenant_extraction ON extraction USING (owner_id = current_setting('oslo.current_owner_id')::uuid);
CREATE POLICY tenant_lab_value ON lab_value USING (owner_id = current_setting('oslo.current_owner_id')::uuid);
CREATE POLICY tenant_prescription ON prescription USING (owner_id = current_setting('oslo.current_owner_id')::uuid);
CREATE POLICY tenant_timeline ON timeline_event USING (owner_id = current_setting('oslo.current_owner_id')::uuid);
CREATE POLICY tenant_emergency ON emergency_profile USING (
  profile_id IN (SELECT profile_id FROM profile WHERE owner_id = current_setting('oslo.current_owner_id')::uuid)
);
CREATE POLICY tenant_consent ON consent USING (owner_id = current_setting('oslo.current_owner_id')::uuid);
CREATE POLICY tenant_share ON share_link USING (owner_id = current_setting('oslo.current_owner_id')::uuid);
CREATE POLICY tenant_tele ON teleconsult_session USING (owner_id = current_setting('oslo.current_owner_id')::uuid);
CREATE POLICY tenant_tele_msg ON teleconsult_message USING (
  session_id IN (SELECT session_id FROM teleconsult_session WHERE owner_id = current_setting('oslo.current_owner_id')::uuid)
);
CREATE POLICY tenant_embedding ON document_embedding USING (owner_id = current_setting('oslo.current_owner_id')::uuid);
