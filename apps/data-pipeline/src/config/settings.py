from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    python_env: str = Field(default="development", alias="PYTHON_ENV")
    supabase_url: str = Field(default="https://example.supabase.co", alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(default="placeholder-service-role-key", alias="SUPABASE_SERVICE_ROLE_KEY")
    database_url: str = Field(default="postgresql://user:pass@localhost:5432/fcc", alias="DATABASE_URL")
    supabase_storage_bucket: str = Field(default="market-datasets", alias="SUPABASE_STORAGE_BUCKET")
    pipeline_batch_size: int = Field(default=500, alias="PIPELINE_BATCH_SIZE")
    sdi_min_evidence_count: int = Field(default=5, alias="SDI_MIN_EVIDENCE_COUNT")
    decay_min_snapshots: int = Field(default=3, alias="DECAY_MIN_SNAPSHOTS")
    decay_threshold: float = Field(default=-0.10, alias="DECAY_THRESHOLD")


settings = Settings()
