from fastapi import FastAPI

from localmind.core.logging import configure_logging, health_payload
from localmind.core.settings import Settings


def create_app() -> FastAPI:
    settings = Settings()
    settings.ensure_data_dir()
    configure_logging(settings)

    app = FastAPI(title="LocalMind", version="0.1.0")
    app.state.settings = settings

    @app.get("/health")
    async def health() -> dict[str, str]:
        return health_payload(settings)

    return app
