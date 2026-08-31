# ==============================================================================
# Unit tests — Health check routes
# Tests all three health endpoints: /health, /health/live, /health/ready
# ==============================================================================

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestLiveness:
    """GET /api/v1/health/live — liveness probe."""

    def test_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200

    def test_returns_alive_status(self, client: TestClient) -> None:
        response = client.get("/api/v1/health/live")
        body = response.json()
        assert body["status"] == "alive"

    def test_no_auth_required(self, client: TestClient) -> None:
        """Liveness must not require authentication — probes run unauthenticated."""
        response = client.get("/api/v1/health/live")
        assert response.status_code != 401
        assert response.status_code != 403


class TestReadiness:
    """GET /api/v1/health/ready — readiness probe."""

    def test_returns_200_in_mock_mode(self, client: TestClient) -> None:
        """In Phase 0 mock mode, the service is always ready."""
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200

    def test_returns_ready_status(self, client: TestClient) -> None:
        response = client.get("/api/v1/health/ready")
        body = response.json()
        assert body["status"] == "ready"

    def test_includes_detection_mode(self, client: TestClient) -> None:
        response = client.get("/api/v1/health/ready")
        body = response.json()
        assert "detection_mode" in body

    def test_detection_mode_is_mock(self, client: TestClient) -> None:
        """Default detection mode in tests must be mock."""
        response = client.get("/api/v1/health/ready")
        body = response.json()
        assert body["detection_mode"] == "mock"


class TestAggregatedHealth:
    """GET /api/v1/health — aggregated health with component status."""

    def test_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_response_schema(self, client: TestClient) -> None:
        """Verify all required fields are present."""
        response = client.get("/api/v1/health")
        body = response.json()

        required_fields = {
            "status",
            "version",
            "app_env",
            "timestamp",
            "uptime_seconds",
            "detection_mode",
            "components",
        }
        assert required_fields.issubset(body.keys())

    def test_status_is_healthy(self, client: TestClient) -> None:
        """Phase 0 — all deps are mocked, overall status must be healthy."""
        response = client.get("/api/v1/health")
        body = response.json()
        # In Phase 0, all components return "not_configured" (mock),
        # which should aggregate to "healthy" (no unhealthy/degraded components)
        assert body["status"] == "healthy"

    def test_has_components_list(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        body = response.json()
        assert isinstance(body["components"], list)
        assert len(body["components"]) > 0

    def test_component_schema(self, client: TestClient) -> None:
        """Each component must have name and status fields."""
        response = client.get("/api/v1/health")
        body = response.json()
        for component in body["components"]:
            assert "name" in component
            assert "status" in component

    def test_includes_kafka_component(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        body = response.json()
        names = [c["name"] for c in body["components"]]
        assert "kafka" in names

    def test_includes_models_component(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        body = response.json()
        names = [c["name"] for c in body["components"]]
        assert "models" in names

    def test_uptime_is_positive(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        body = response.json()
        assert body["uptime_seconds"] >= 0

    def test_timestamp_is_iso8601(self, client: TestClient) -> None:
        from datetime import datetime

        response = client.get("/api/v1/health")
        body = response.json()
        # Should not raise
        datetime.fromisoformat(body["timestamp"])


class TestRequestId:
    """Every response must include an X-Request-ID header."""

    @pytest.mark.parametrize(
        "path",
        ["/api/v1/health", "/api/v1/health/live", "/api/v1/health/ready"],
    )
    def test_response_includes_request_id(self, client: TestClient, path: str) -> None:
        response = client.get(path)
        assert "x-request-id" in response.headers

    def test_custom_request_id_is_echoed(self, client: TestClient) -> None:
        custom_id = "test-request-123"
        response = client.get(
            "/api/v1/health/live",
            headers={"X-Request-ID": custom_id},
        )
        assert response.headers.get("x-request-id") == custom_id

    def test_generated_request_id_is_uuid(self, client: TestClient) -> None:
        import uuid

        response = client.get("/api/v1/health/live")
        returned_id = response.headers.get("x-request-id", "")
        # Should be a valid UUID
        uuid.UUID(returned_id)  # Raises if invalid


class TestApiVersioning:
    """Verify the /api/v1 prefix is applied consistently."""

    def test_root_returns_service_info(self, client: TestClient) -> None:
        response = client.get("/")
        body = response.json()
        assert "service" in body
        assert "version" in body
        assert "health" in body

    def test_openapi_schema_accessible(self, client: TestClient) -> None:
        response = client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema.get("openapi", "").startswith("3.")

    def test_docs_accessible(self, client: TestClient) -> None:
        response = client.get("/api/v1/docs")
        assert response.status_code == 200

    def test_redoc_accessible(self, client: TestClient) -> None:
        response = client.get("/api/v1/redoc")
        assert response.status_code == 200
