"""One-off script to clean up demo data in Supabase."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DB_URL = "postgresql+asyncpg://postgres.wwpmsomikexvghstwyli:oslo%40medical123@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"
DEMO_OWNER = "00000000-0000-4000-a000-000000000001"

async def main():
    engine = create_async_engine(DB_URL)
    async with engine.begin() as conn:
        tables = [
            "smart_report_cache",
            "document_embedding",
            "lab_value",
            "extraction",
            "timeline_event",
            "prescription",
            "document",
        ]
        for t in tables:
            result = await conn.execute(
                text(f"DELETE FROM {t} WHERE owner_id = :oid"),
                {"oid": DEMO_OWNER},
            )
            print(f"  {t}: deleted {result.rowcount} rows")
    
    print("\nCleanup complete!")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
