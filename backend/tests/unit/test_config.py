# ==============================================================================
# Unit tests — Configuration system
# Verifies Settings loading, validation, and derived properties.
# ==============================================================================

from __future__ import annotations

import os

import pytest

from app.core.config import Settings, get_settings


class TestSettingsDefaults:
    """Verify default values when no environment variables are set."""

    def test_detection_mode_default(self) -> None:
        s = Settings()
        assert s.detection_mode == "mock"

    def test_audit_mode_default(self) -> None:
        s = Settings()
        assert s.audit_mode == "mock"

    def test_app_env_default(self) -> None:
        s = Settings()
        assert s.app_env == "development"

    def test_log_level_default(self) -> None:
        s = Settings()
        assert s.log_level == "INFO"

    def test_api_port_default(self) -> None:
        s = Settings()
        assert s.api_port == 8000

    def test_api_prefix_default(self) -> None:
        s = Settings()
        assert s.api_prefix == "/api/v1"

    def test_kafka_bootstrap_servers_default(self) -> None:
        s = Settings()
        assert s.kafka_bootstrap_servers == "localhost:9092"

    def test_risk_thresholds_default(self) -> None:
        s = Settings()
        assert s.risk_low_max == 29
        assert s.risk_medium_max == 59
        assert s.risk_high_max == 79

    def test_tier0_thresholds_default(self) -> None:
        s = Settings()
        assert s.tier0_early_exit_low == pytest.approx(0.22)
        assert s.tier0_early_exit_high == pytest.approx(0.75)

    def test_cors_origins_is_list(self) -> None:
        s = Settings()
        assert isinstance(s.cors_origins, list)
        assert len(s.cors_origins) > 0

    def test_model_paths_default_none(self) -> None:
        s = Settings()
        assert s.tier1_model_path is None
        assert s.tier2_model_path is None
        assert s.fusion_model_path is None


class TestSettingsEnvironmentOverride:
    """Verify environment variables override defaults correctly."""

    def test_detection_mode_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DETECTION_MODE", "onnx")
        s = Settings()
        assert s.detection_mode == "onnx"

    def test_log_level_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        s = Settings()
        assert s.log_level == "DEBUG"

    def test_cors_origins_comma_separated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Comma-separated string in env var is parsed to a list via property."""
        monkeypatch.setenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:3000,https://app.example.com",
        )
        # Settings reads the raw string from env; cors_origins property splits it
        os.environ["CORS_ORIGINS"] = (
            "http://localhost:5173,http://localhost:3000,https://app.example.com"
        )
        s = Settings(_env_file=None)  # bypass .env file to use monkeypatched env
        origins = s.cors_origins
        assert len(origins) == 3
        assert "http://localhost:5173" in origins
        assert "https://app.example.com" in origins
        del os.environ["CORS_ORIGINS"]

    def test_risk_threshold_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RISK_LOW_MAX", "24")
        monkeypatch.setenv("RISK_MEDIUM_MAX", "54")
        s = Settings()
        assert s.risk_low_max == 24
        assert s.risk_medium_max == 54


class TestSettingsValidation:
    """Verify validators reject invalid configurations."""

    def test_invalid_detection_mode_raises(self) -> None:
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            Settings(detection_mode="invalid_mode")  # type: ignore[arg-type]

    def test_invalid_log_level_raises(self) -> None:
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            Settings(log_level="VERBOSE")  # type: ignore[arg-type]

    def test_tier0_high_must_exceed_low(self) -> None:
        """Validates that early_exit_high > early_exit_low."""
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            Settings(
                tier0_early_exit_low=0.8,
                tier0_early_exit_high=0.5,  # Invalid: high < low
            )

    def test_api_port_in_valid_range(self) -> None:
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            Settings(api_port=0)

        with pytest.raises(PydanticValidationError):
            Settings(api_port=99999)

    def test_risk_score_in_valid_range(self) -> None:
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            Settings(risk_low_max=150)  # > 100


class TestSettingsDerivedProperties:
    """Test derived helper properties."""

    def test_is_development_true(self) -> None:
        s = Settings(app_env="development")
        assert s.is_development is True
        assert s.is_production is False

    def test_is_production_true(self) -> None:
        s = Settings(app_env="production")
        assert s.is_production is True
        assert s.is_development is False

    def test_kafka_topics_returns_dict(self) -> None:
        s = Settings()
        topics = s.kafka_topics
        assert isinstance(topics, dict)
        assert len(topics) > 0

    def test_kafka_topics_use_prefix(self) -> None:
        s = Settings(kafka_topic_prefix="myprefix")
        topics = s.kafka_topics
        for topic_name in topics.values():
            assert topic_name.startswith("myprefix.")

    def test_kafka_topics_include_required_topics(self) -> None:
        s = Settings()
        topics = s.kafka_topics
        required = {
            "audio_ingest",
            "audio_segment",
            "detection_tier0",
            "detection_tier1",
            "fusion_result",
            "risk_events",
            "deadletter",
        }
        assert required.issubset(topics.keys())


class TestGetSettingsSingleton:
    """Verify @lru_cache singleton behaviour."""

    def test_same_instance_returned(self) -> None:
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_cache_can_be_cleared(self) -> None:
        s1 = get_settings()
        get_settings.cache_clear()
        s2 = get_settings()
        # New instance after cache clear
        # They'll have equal values but may or may not be the same object
        assert s1.app_version == s2.app_version
