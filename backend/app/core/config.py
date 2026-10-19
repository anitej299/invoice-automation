from functools import lru_cache
from decimal import Decimal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./invoice.db"
    jwt_secret: str
    jwt_expire_minutes: int = 60
    automation_api_key: str
    seed_admin_email: str = "finance@example.test"
    seed_admin_password: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    extraction_provider: str = "ollama"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout_seconds: float = 120
    ocr_provider: str = "tesseract"
    ocr_api_key: str = ""
    high_value_threshold: Decimal = Decimal("100000")
    due_soon_days: int = 7
    total_tolerance: Decimal = Decimal("0.01")
    min_extraction_confidence: float = 0.75
    finance_email: str = "finance@example.test"
    timezone: str = "Asia/Kolkata"
    max_upload_mb: int = 15
    max_pdf_pages: int = 30
    cors_origins: str = "http://localhost:5173,http://localhost:8080"


@lru_cache
def settings():
    value = Settings()
    if len(value.jwt_secret) < 32 or len(value.automation_api_key) < 32:
        raise ValueError(
            "JWT_SECRET and AUTOMATION_API_KEY must each contain at least 32 characters"
        )
    return value
