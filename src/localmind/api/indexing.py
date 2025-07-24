from fastapi import APIRouter, HTTPException

from localmind.indexing.routes import (
    IndexRepositoryRequest,
    IndexingRouterFactory,
    RegisterRepositoryRequest,
    RepositoryResponse,
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

    return router
