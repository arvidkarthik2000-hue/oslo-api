"""Initial schema — OSLO tables, indexes, RLS, pgvector.

Revision ID: 0001_initial
Revises: None
Create Date: 2026-04-22
"""
from pathlib import Path
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

# SQL lives alongside this file for readability
_SQL_FILE = Path(__file__).resolve().parent.parent.parent / "alembic" / "sql" / "001_initial.sql"


def upgrade() -> None:
    sql = _SQL_FILE.read_text(encoding="utf-8")
    op.execute(sql)


def downgrade() -> None:
    # Reverse order: drop policies, disable RLS, drop tables
    # Only safe on a fresh DB — production downgrades should be manual
    tables = [
        "document_embedding", "audit_event", "teleconsult_message",
        "teleconsult_session", "rmp", "share_link", "consent",
        "emergency_profile", "timeline_event", "prescription",
        "lab_value", "extraction", "document", "profile", "owner",
    ]
    for t in tables:
        op.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
    op.execute("DROP EXTENSION IF EXISTS vector")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
