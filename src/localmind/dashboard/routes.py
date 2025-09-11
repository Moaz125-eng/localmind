from pathlib import Path

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from localmind.core.settings import Settings
from localmind.dashboard.progress import progress_hub


def build_dashboard_router(settings: Settings) -> APIRouter:
    router = APIRouter(tags=["dashboard"])
    templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

    @router.get("/", response_class=HTMLResponse)
    async def dashboard_home(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "service_name": "LocalMind",
                "ollama_model": settings.ollama_model,
                "embedding_model": settings.embedding_model,
            },
        )

    @router.websocket("/ws/indexing/{repository_id}")
    async def indexing_progress(websocket: WebSocket, repository_id: int) -> None:
        await websocket.accept()
        try:
            async for payload in progress_hub.subscribe(repository_id):
                await websocket.send_text(payload)
        except WebSocketDisconnect:
            return

    return router
