from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

router = APIRouter()


@router.get("/")
async def browse_dataset(
    model_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
) -> dict:
    """Paginated confirmed-pair table for a model."""
    # TODO: query PostgreSQL
    raise NotImplementedError


@router.get("/download")
async def download_dataset(
    model_id: str,
    fmt: str = Query("parquet", pattern="^(parquet|csv|json)$"),
) -> StreamingResponse:
    """Stream the full confirmed dataset as parquet / csv / json."""
    # TODO: pull from HF Hub and stream
    raise NotImplementedError
