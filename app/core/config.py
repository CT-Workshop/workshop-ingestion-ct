from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "doc-ingestion-service"
    environment: str = "development"
    log_level: str = "INFO"

    jwt_issuer: str = "https://auth.example.com"
    jwt_audience: str = "doc-ingestion"
    service_master_key: str = ""

    max_upload_bytes: int = 26_214_400  # 25 MiB
    allowed_extensions: str = ".pdf,.docx,.xlsx"

    storage_bucket: str = "ingestion-demo-bucket"
    presigned_url_ttl_seconds: int = 900
    upload_temp_dir: str = "/tmp/doc-ingestion-uploads"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def allowed_ext_set() -> set[str]:
    s = get_settings().allowed_extensions
    return {e.strip().lower() for e in s.split(",") if e.strip()}
