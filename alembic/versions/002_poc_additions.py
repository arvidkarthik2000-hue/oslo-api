"""POC additions — wearable_reading, smart_report_cache, document processing_status.

Revision ID: 0002_poc
Revises: 0001_initial
Create Date: 2026-04-23
"""
from pathlib import Path
from alembic import op

revision = "0002_poc"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

_SQL_FILE = Path(__file__).resolve().parent.parent / "sql" / "002_poc_additions.sql"


def upgrade() -> None:
    sql = _SQL_FILE.read_text(encoding="utf-8")
    op.execute(sql)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS smart_report_cache CASCADE")
    op.execute("DROP TABLE IF EXISTS wearable_reading CASCADE")
    op.execute("ALTER TABLE document DROP COLUMN IF EXISTS processing_status")
    op.execute("ALTER TABLE extraction DROP COLUMN IF EXISTS explanation_markdown")
    op.execute("ALTER TABLE extraction DROP COLUMN IF EXISTS explanation_generated_at")
