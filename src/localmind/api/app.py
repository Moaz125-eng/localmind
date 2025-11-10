from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from localmind.api.analysis import build_analysis_router
from localmind.api.chat import build_chat_router
from localmind.api.embeddings import build_embedding_router
from localmind.api.insights import build_insights_router
from localmind.api.review import build_review_router
from localmind.dashboard.routes import build_dashboard_router
from localmind.api.docs import build_docs_router
from localmind.api.indexing import build_indexing_router
from localmind.api.saved_search import build_saved_search_router
from localmind.api.runtime import build_runtime_router
from localmind.api.search import build_search_router
from localmind.core.logging import configure_logging, health_payload
from localmind.core.settings import Settings
from localmind.indexing.database import Database
from localmind.indexing.routes import IndexingRouterFactory


def create_app() -> FastAPI:
    settings = Settings()
    settings.ensure_data_dir()
    configure_logging(settings)
    database = Database(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await database.init()
        app.state.database = database
        yield

    app = FastAPI(title="LocalMind", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.database = database
    app.include_router(
        build_indexing_router(IndexingRouterFactory(database, settings.exclude_patterns))
    )
    app.include_router(build_docs_router(database, settings.exclude_patterns))
    app.include_router(build_analysis_router(database))
    app.include_router(build_embedding_router(database, settings))
    app.include_router(build_search_router(settings))
    app.include_router(build_saved_search_router(database, settings))
    app.include_router(build_runtime_router(settings))
    app.include_router(build_chat_router(settings))
    app.include_router(build_insights_router(database, settings))
    app.include_router(build_review_router(database, settings))
    app.include_router(build_dashboard_router(settings))

    @app.get("/health")
    async def health() -> dict[str, str]:
        return health_payload(settings)

    return app
