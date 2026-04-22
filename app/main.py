"""OSLO API — FastAPI application entry point."""
import sentry_sdk
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, profiles, consents, documents, health, emergency
from app.middleware.audit import AuditMiddleware

settings = get_settings()
is_dev = settings.environment == "development"

# Sentry
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=0.1 if settings.environment == "production" else 1.0,
        send_default_pii=False,  # DPDP: never send PII to Sentry
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    from app.database import engine
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if is_dev else None,
    redoc_url="/redoc" if is_dev else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if is_dev else ["https://oslo-doctor.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit middleware
app.add_middleware(AuditMiddleware)

# Routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(profiles.router, prefix="/profiles", tags=["Profiles"])
app.include_router(consents.router, prefix="/consents", tags=["Consents"])
app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(emergency.router, prefix="/profiles", tags=["Emergency"])
