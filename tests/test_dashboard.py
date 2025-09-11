import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from localmind.api.app import create_app
from localmind.dashboard.progress import IndexProgressEvent, IndexProgressHub


def test_dashboard_home_renders() -> None:
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    assert "LocalMind" in response.text
    assert "Semantic Search" in response.text


@pytest.mark.asyncio
async def test_progress_hub_broadcasts_events() -> None:
    hub = IndexProgressHub()
    queue_payloads: list[str] = []

    async def collect() -> None:
        async for payload in hub.subscribe(7):
            queue_payloads.append(payload)
            break

    task = asyncio.create_task(collect())
    await asyncio.sleep(0.05)
    await hub.publish(
        IndexProgressEvent(
            repository_id=7,
            stage="scan",
            processed=2,
            total=10,
            message="Scanning files",
        )
    )
    await task
    assert queue_payloads
    assert "scan" in queue_payloads[0]
