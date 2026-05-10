"""Smoke tests for REST endpoints (no real Firestore — get_firestore is mocked)."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_firestore():
    """Avoid needing the Firestore emulator or cloud credentials for health checks."""
    with patch("routes.health_routes.get_firestore") as m:
        m.return_value.collection.return_value.document.return_value.get.return_value = (
            MagicMock()
        )
        yield m


def test_health_root_returns_200(client):
    r = client.get("/api/health/")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("status") in ("healthy", "degraded")


def test_swagger_docs_available(client):
    # Flask-RESTX serves the Swagger UI at /swagger (not under /api); OpenAPI JSON is /api/swagger.json
    r = client.get("/swagger")
    assert r.status_code == 200


def test_openapi_json_available(client):
    r = client.get("/api/swagger.json")
    assert r.status_code == 200
    assert "paths" in r.get_json()


def test_registered_namespaces_have_paths(client):
    spec = client.get("/api/swagger.json").get_json()
    paths = spec.get("paths") or {}
    # Spot-check namespaces from app.py (Firebase mode)
    assert any("/drivers" in p for p in paths)
    assert any("/customers" in p for p in paths)
    assert any("/health" in p for p in paths)
