"""Application configuration via environment variables."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "OSLO API"
    app_version: str = "0.1.0"
    environment: str = "development"  # development | staging | production

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/oslo"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # JWT
    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 30

    # MSG91 OTP
    msg91_auth_key: str = ""
    msg91_template_id: str = ""
    msg91_otp_length: int = 6
    msg91_otp_expiry_minutes: int = 5

    # AWS
    aws_region: str = "ap-south-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    s3_bucket_name: str = "oslo-docs-mumbai"
    kms_master_key_id: str = ""

    # AI Service
    ai_service_base_url: str = "https://oslo-ai.example.com"
    ai_service_api_key: str = ""
    ai_service_timeout_seconds: int = 30

    # Razorpay
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    # Sentry
    sentry_dsn: str = ""

    # Rate limits
    otp_rate_limit_per_hour: int = 5
    otp_rate_limit_per_day_per_ip: int = 10
    ask_ai_free_monthly_limit: int = 10
    re_extract_daily_limit: int = 3

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False, "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
