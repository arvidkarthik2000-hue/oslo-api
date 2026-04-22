# Day 01 — 2026-04-23

## Completed (committed files only)

### oslo-api — commit 57fb206
- `alembic/sql/002_poc_additions.sql` — wearable_reading + smart_report_cache tables, processing_status on document, explanation fields on extraction, RLS policies
- `alembic/versions/002_poc_additions.py` — Alembic revision linking to 001
- `app/models/wearable_reading.py` — SQLAlchemy model for Health Connect data
- `app/models/smart_report_cache.py` — SQLAlchemy model for cached Smart Report/Timeline Summary
- `app/models/__init__.py` — registered new models
- `app/services/ai_service_mock.py` — comprehensive mock responses: 12 Indian lab tests, 3 medications, Smart Report markdown, explanation, timeline summary, ask with refusal detection
- `app/services/ai_service.py` — HTTP client with auto mock fallback when AI_SERVICE_BASE_URL is empty
- `app/dependencies.py` — dev-mode optional auth with DEMO_OWNER_ID, auto-create demo owner
- `app/routers/auth.py` — new /dev-create endpoint for POC
- `app/schemas/auth.py` — DevCreateResponse schema
- `app/routers/documents.py` — full classify→extract→denormalize→timeline pipeline (create, finalize, list, counts, detail, correct, explain)
- `app/schemas/document.py` — upload/finalize/list/detail/correction/explain schemas
- `app/routers/timeline.py` — list with filters/search/date range, note, voice-note, summarize with cache
- `app/schemas/timeline.py` — timeline schemas
- `app/main.py` — wired timeline router
- Migration 002 applied to Supabase Mumbai ✅

## Gate Day 1
- [x] Document pipeline: create → finalize (classify + extract + denormalize) → timeline event creation
- [x] Timeline router with filter, search, date range, notes, voice notes, AI summary
- [x] Dev-mode auth bypass with DEMO_OWNER_ID
- [x] All routes import-verified (32 routes total)
- [x] Migration 002 applied to Supabase

## Blockers
- Supabase pooler port 5432 blocked from this machine; used port 6543 (transaction mode) for migration
- AI endpoint not live yet (expected Day 3) — mocks active

## Bugs found and resolved
- PowerShell `&&` syntax error — used semicolons throughout
- Alembic env.py connection refused on port 5432 — direct asyncpg on port 6543 works

## Tomorrow's plan
- Day 2: Extraction review screen polish, Timeline tab with real data, Records tab, Lab report detail screen
- Wire /documents/{id}/compare endpoint for same-lab comparison
- Pre-load demo data if XQZ delivers the anonymized reports zip
