import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timezone

from localmind.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class IndexProgressEvent:
    repository_id: int
    stage: str
    processed: int
    total: int
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_json(self) -> str:
        return json.dumps(
            {
                "repository_id": self.repository_id,
                "stage": self.stage,
                "processed": self.processed,
                "total": self.total,
                "message": self.message,
                "timestamp": self.timestamp,
            }
        )


class IndexProgressHub:
    def __init__(self) -> None:
        self._subscribers: dict[int, list[asyncio.Queue[str]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, repository_id: int) -> AsyncIterator[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        async with self._lock:
            self._subscribers.setdefault(repository_id, []).append(queue)
        try:
            while True:
                payload = await queue.get()
                yield payload
        finally:
            async with self._lock:
                listeners = self._subscribers.get(repository_id, [])
                if queue in listeners:
                    listeners.remove(queue)

    async def publish(self, event: IndexProgressEvent) -> None:
        payload = event.to_json()
        async with self._lock:
            listeners = list(self._subscribers.get(event.repository_id, []))
        for queue in listeners:
            await queue.put(payload)

    async def emit_stage(
        self,
        repository_id: int,
        stage: str,
        processed: int,
        total: int,
        message: str,
    ) -> None:
        await self.publish(
            IndexProgressEvent(
                repository_id=repository_id,
                stage=stage,
                processed=processed,
                total=total,
                message=message,
            )
        )


progress_hub = IndexProgressHub()
