"""
Search route — embeds a query and returns top-K nearest confirmed pairs
from the model's static FAISS index.

The IdentificationModel for each model_id is loaded once at first request
and cached in memory for the lifetime of the process. The index is never
rebuilt at query time.
"""

from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from framework.embedder import IdentificationModel

router = APIRouter()


class SearchResult(BaseModel):
    post_id: str
    description: str
    answer: str
    flair: str | None
    confidence: float
    similarity: float
    created_utc: int


@router.get("/", response_model=list[SearchResult])
async def search(
    model_id: str,
    q: str = Query(..., min_length=1, description="Vague description to search for"),
    top_k: int = Query(10, ge=1, le=50),
) -> list[SearchResult]:
    model = _load_model(model_id)
    results = model.search(q, top_k=top_k)
    return [
        SearchResult(
            post_id=pair.post_id,
            description=pair.description,
            answer=pair.answer,
            flair=pair.flair,
            confidence=pair.confidence,
            similarity=score,
            created_utc=pair.created_utc,
        )
        for pair, score in results
    ]


@lru_cache(maxsize=16)
def _load_model(model_id: str) -> IdentificationModel:
    path = f"models/{model_id}/identification_model"
    try:
        return IdentificationModel(path, path).load()
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found or not trained: {exc}")
