# ==============================================================================
# VAANI-RAKSHAK — Application Configuration
# All settings are sourced from environment variables (or a .env file).
# Never hardcode secrets, URLs, or thresholds in source code.
# ==============================================================================

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralised application settings.

    Sources (in priority order):
      1. OS environment variables
      2. .env file (loaded automatically when present)
      3. Default values defined here
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    # --------------------------------------------------------------------------
    # Application identity
    # --------------------------------------------------------------------------
    app_env: Literal["development", "staging", "production"] = "development"
    app_version: str = "0.1.0"
    app_name: str = "VAANI-RAKSHAK Backend"

    # --------------------------------------------------------------------------
    # Logging
    # --------------------------------------------------------------------------
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_json: bool = False  # True → JSON lines (production); False → pretty console

    # --------------------------------------------------------------------------
    # API Server
    # --------------------------------------------------------------------------
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    api_prefix: str = "/api/v1"

    # Stored as a comma-separated string so pydantic-settings reads it cleanly
    # from environment variables.  Use the `cors_origins_list` property.
    cors_origins_raw: str = Field(
        default="http://localhost:5173,http://localhost:4173,http://localhost:3000",
        alias="cors_origins",
    )

    max_audio_size_mb: int = Field(default=50, ge=1, le=500)

    # --------------------------------------------------------------------------
    # Detection Mode
    # --------------------------------------------------------------------------
    detection_mode: Literal["mock", "onnx"] = "mock"

    # Mock adapter scenario for deterministic testing
    mock_scenario: str = "LOW_RISK"

    # --------------------------------------------------------------------------
    # Kafka
    # --------------------------------------------------------------------------
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_security_protocol: str = "PLAINTEXT"
    kafka_topic_prefix: str = "vaani"

    # Producer
    kafka_producer_acks: str = "all"
    kafka_producer_retries: int = Field(default=3, ge=0)
    kafka_producer_linger_ms: int = Field(default=5, ge=0)

    # Consumer
    kafka_consumer_group_id: str = "vaani-pipeline"
    kafka_consumer_auto_offset_reset: Literal["latest", "earliest"] = "latest"

    # --------------------------------------------------------------------------
    # Detection Cascade Thresholds
    # --------------------------------------------------------------------------
    tier0_early_exit_low: float = Field(default=0.22, ge=0.0, le=1.0)
    tier0_early_exit_high: float = Field(default=0.75, ge=0.0, le=1.0)
    tier1_early_exit_low: float = Field(default=0.35, ge=0.0, le=1.0)
    tier1_early_exit_high: float = Field(default=0.70, ge=0.0, le=1.0)
    tier1_escalate_threshold: float = Field(default=0.50, ge=0.0, le=1.0)
    tier_disagreement_delta: float = Field(default=0.30, ge=0.0, le=1.0)

    high_stakes_transaction_inr: int = Field(default=200_000, ge=0)

    # --------------------------------------------------------------------------
    # Risk Engine Thresholds
    # DEVELOPMENT DEFAULTS — not production-validated.
    # --------------------------------------------------------------------------
    risk_low_max: int = Field(default=29, ge=0, le=100)
    risk_medium_max: int = Field(default=59, ge=0, le=100)
    risk_high_max: int = Field(default=79, ge=0, le=100)

    oob_high_stakes_threshold: int = Field(default=55, ge=0, le=100)
    oob_default_threshold: int = Field(default=70, ge=0, le=100)

    # --------------------------------------------------------------------------
    # Model Paths (Phase 1+ — unused in Phase 0)
    # --------------------------------------------------------------------------
    tier0_model_path: str | None = None
    tier1_model_path: str | None = None
    tier2_model_path: str | None = None
    speaker_model_path: str | None = None
    lid_model_path: str | None = None
    fusion_model_path: str | None = None

    # --------------------------------------------------------------------------
    # Audit Ledger (Phase 8)
    # --------------------------------------------------------------------------
    audit_mode: Literal["mock", "fabric"] = "mock"

    # --------------------------------------------------------------------------
    # Telephony Simulation (Phase 7)
    # --------------------------------------------------------------------------
    telephony_mode: Literal["simulated", "freeswitch", "kamailio"] = "simulated"
    simulated_segment_duration_ms: int = Field(default=2000, ge=100)
    simulated_sample_rate: int = Field(default=16000, ge=8000)

    # --------------------------------------------------------------------------
    # Hardening & Security (Phase 9)
    # --------------------------------------------------------------------------
    max_request_size_mb: int = Field(default=50, ge=1)
    max_audio_chunk_size_mb: int = Field(default=10, ge=1)

    rate_limit_requests_per_minute: int = Field(default=120, ge=1)
    rate_limit_burst_capacity: int = Field(default=30, ge=1)

    ws_max_message_size_mb: int = Field(default=5, ge=1)
    ws_max_messages_per_second: int = Field(default=20, ge=1)
    ws_max_connections_per_client: int = Field(default=10, ge=1)

    enable_hsts: bool = Field(default=False)

    circuit_breaker_failure_threshold: int = Field(default=5, ge=1)
    circuit_breaker_recovery_timeout_sec: float = Field(default=30.0, ge=1.0)
    circuit_breaker_half_open_max_trials: int = Field(default=3, ge=1)

    slow_request_threshold_ms: float = Field(default=500.0, ge=10.0)

    # --------------------------------------------------------------------------
    # Validators
    # --------------------------------------------------------------------------
    @field_validator("cors_origins_raw", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> str:
        """Normalise list → comma-separated string if constructed programmatically."""
        if isinstance(v, list):
            return ",".join(str(x) for x in v)
        return str(v)

    @field_validator("tier0_early_exit_high")
    @classmethod
    def high_must_exceed_low(cls, v: float, info: object) -> float:
        data = getattr(info, "data", {})
        low = data.get("tier0_early_exit_low", 0.22)
        if v <= low:
            msg = "tier0_early_exit_high must be greater than tier0_early_exit_low"
            raise ValueError(msg)
        return v

    # --------------------------------------------------------------------------
    # Derived helpers
    # --------------------------------------------------------------------------
    @property
    def cors_origins(self) -> list[str]:
        """Return CORS origins as a list (split from comma-separated raw string)."""
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def kafka_topics(self) -> dict[str, str]:
        """Fully-qualified topic names with prefix applied."""
        p = self.kafka_topic_prefix
        return {
            "audio_ingest": f"{p}.audio.ingest",
            "audio_segment": f"{p}.audio.segment",
            "detection_tier0": f"{p}.detection.tier0",
            "detection_tier1": f"{p}.detection.tier1",
            "detection_tier2": f"{p}.detection.tier2",
            "detection_prosody": f"{p}.detection.prosody",
            "detection_speaker": f"{p}.detection.speaker",
            "fusion_result": f"{p}.fusion.result",
            "risk_events": f"{p}.risk.events",
            "workflow_events": f"{p}.workflow.events",
            "audit_events": f"{p}.audit.events",
            "deadletter": f"{p}.deadletter",
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the singleton Settings instance.

    Uses @lru_cache so settings are parsed once per process.
    In tests, call get_settings.cache_clear() to reset.
    """
    return Settings()
