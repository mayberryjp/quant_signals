"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = ""

    # Redis TTL defaults (seconds)
    signal_record_ttl: int = 7 * 24 * 3600          # 7 days
    idempotency_key_ttl: int = 24 * 3600             # 24 hours
    watchlist_entry_ttl: int = 30 * 24 * 3600        # 30 days
    source_record_ttl: int = 90 * 24 * 3600          # 90 days
    maintenance_heartbeat_ttl: int = 5 * 60          # 5 minutes

    # Symbol master lookup API (GET {base}/symbols/by-ticker/{TICKER})
    symbol_api_base_url: str = "https://signals.quant.mayberry.farm"
    symbol_api_timeout: float = 5.0
    symbol_api_cache_ttl: int = 300

    # Validation limits
    max_tags: int = 20
    max_metadata_bytes: int = 16_384
    max_reason_length: int = 2000
    max_page_size: int = 100
    default_page_size: int = 25

    model_config = {"env_prefix": "QUANT_"}


settings = Settings()
