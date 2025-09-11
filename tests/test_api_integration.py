from pathlib import Path

from fastapi.testclient import TestClient

from localmind.api.app import create_app


def test_api_route_registration() -> None:
    client = TestClient(create_app())
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    paths = openapi.json()["paths"]
    assert "/repositories" in paths
    assert "/search" in paths
    assert "/chat" in paths
    assert "/review/pull-request" in paths
    assert "/insights/duplicates" in paths


def test_repository_validation_error() -> None:
    client = TestClient(create_app())
    response = client.post("/repositories", json={"name": "", "root_path": "/tmp"})
    assert response.status_code == 422


def test_search_validation_error() -> None:
    client = TestClient(create_app())
    response = client.post("/search", json={"query": ""})
    assert response.status_code == 422
