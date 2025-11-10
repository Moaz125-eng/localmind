from dataclasses import dataclass

import httpx

from localmind.core.settings import Settings


@dataclass(frozen=True)
class OllamaModelInfo:
    name: str
    size_bytes: int
    modified_at: str


@dataclass(frozen=True)
class OllamaHealthStatus:
    reachable: bool
    base_url: str
    configured_model: str
    model_available: bool
    model_count: int
    error: str | None = None


class OllamaRuntime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.configured_model = settings.ollama_model

    async def list_models(self) -> list[OllamaModelInfo]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            payload = response.json()
        models: list[OllamaModelInfo] = []
        for item in payload.get("models", []):
            models.append(
                OllamaModelInfo(
                    name=str(item.get("name", "")),
                    size_bytes=int(item.get("size", 0)),
                    modified_at=str(item.get("modified_at", "")),
                )
            )
        return models

    async def health(self) -> OllamaHealthStatus:
        try:
            models = await self.list_models()
            names = {model.name for model in models}
            configured_available = any(
                self.configured_model == name or name.startswith(f"{self.configured_model}:")
                for name in names
            )
            return OllamaHealthStatus(
                reachable=True,
                base_url=self.base_url,
                configured_model=self.configured_model,
                model_available=configured_available,
                model_count=len(models),
            )
        except Exception as exc:
            return OllamaHealthStatus(
                reachable=False,
                base_url=self.base_url,
                configured_model=self.configured_model,
                model_available=False,
                model_count=0,
                error=str(exc),
            )

    async def pull_model(self, model_name: str) -> dict[str, object]:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name, "stream": False},
            )
            response.raise_for_status()
            return response.json()
