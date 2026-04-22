"""Database engine, session, and tenant context helpers."""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.environment == "development",
)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """Dependency that yields a database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def set_tenant_context(db: AsyncSession, owner_id: UUID) -> None:
    """Set RLS tenant context for the current transaction.
    
    Every request sets this so Postgres RLS policies can enforce
    tenant isolation at the database level.
    """
    await db.execute(text(f"SET LOCAL oslo.current_owner_id = '{owner_id}'"))
