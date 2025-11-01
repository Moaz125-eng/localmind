from fastapi import APIRouter, HTTPException, Query

from localmind.indexing.routes import (
    EnqueueIndexRequest,
    IndexRepositoryRequest,
    IndexingRouterFactory,
    RegisterRepositoryRequest,
    RepositoryResponse,
    TaskResponse,
)


def build_indexing_router(factory: IndexingRouterFactory) -> APIRouter:
    router = APIRouter(prefix="/repositories", tags=["indexing"])

    @router.get("", response_model=list[RepositoryResponse])
    async def list_repositories() -> list[RepositoryResponse]:
        return await factory.list_repositories()

    @router.post("", response_model=RepositoryResponse)
    async def register_repository(payload: RegisterRepositoryRequest) -> RepositoryResponse:
        return await factory.register_repository(payload)

    @router.post("/{repository_id}/index")
    async def index_repository(
        repository_id: int, payload: IndexRepositoryRequest
    ) -> dict[str, object]:
        try:
            return await factory.index_repository(repository_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/{repository_id}/index/tasks", response_model=TaskResponse)
    async def enqueue_index_task(
        repository_id: int, payload: EnqueueIndexRequest
    ) -> TaskResponse:
        try:
            return await factory.enqueue_index(repository_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.post("/index/tasks/{task_id}/run", response_model=TaskResponse)
    async def run_index_task(task_id: int) -> TaskResponse:
        try:
            return await factory.run_index_task(task_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.get("/index/tasks", response_model=list[TaskResponse])
    async def list_index_tasks(
        repository_id: int | None = Query(default=None),
    ) -> list[TaskResponse]:
        return await factory.list_tasks(repository_id)

    return router
