from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_models() -> list[dict]:
    """Return all registered models with summary stats."""
    # TODO: query PostgreSQL for model registry
    raise NotImplementedError
