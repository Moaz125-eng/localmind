import pytest
from fastapi.testclient import TestClient

from localmind.api.app import create_app


def test_request_logging_headers_present() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Request-Id")
    assert response.headers.get("X-Response-Time-Ms")
