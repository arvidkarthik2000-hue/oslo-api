# OSLO API — Day 02 Log (2026-04-22)

## Bug Fixes (commit `defeae0`)

### Bug 1: Alembic silent failure
- Created `alembic/versions/001_initial_schema.py` — proper revision that loads SQL via `op.execute()`
- Moved `migrations/001_initial.sql` → `alembic/sql/001_initial.sql`
- Deleted `migrations/` directory
- Downgrade function drops all tables in reverse order

### Bug 2: docs_url gate
- Changed `settings.debug` → `settings.environment == "development"` for docs_url, redoc_url, CORS
- Removed `debug: bool` from Settings entirely
- Updated `.env.example`, `docker-compose.yml`, `tests/conftest.py` to remove DEBUG references

### Bug 3: Dev-mode OTP bypass
- `send_otp()`: in development, prints `Dev OTP for <phone>: 123456` to stdout, returns valid request_id
- `verify_otp()`: in development, accepts `123456` for any phone
- Gate is purely `settings.environment == "development"` — no longer checks MSG91 key presence
- Unblocks mobile testing without DLT template approval

## Files Changed
- `alembic/versions/001_initial_schema.py` (new)
- `alembic/sql/001_initial.sql` (moved from migrations/)
- `app/config.py` (removed debug field)
- `app/main.py` (gate on environment)
- `app/services/otp_service.py` (dev bypass)
- `.env.example` (removed DEBUG)
- `docker-compose.yml` (removed DEBUG)
- `tests/conftest.py` (removed DEBUG)
