import logging
from typing import Any

from localmind.core.settings import Settings


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def health_payload(settings: Settings) -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "localmind",
        "data_dir": str(settings.data_dir),
        "embedding_model": settings.embedding_model,
        "ollama_model": settings.ollama_model,
    }
