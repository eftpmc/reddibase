from fastapi import APIRouter, Query
from pydantic import BaseModel

from api.model_loader import get_model

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
    q: str = Query(..., min_length=1),
    top_k: int = Query(10, ge=1, le=50),
) -> list[SearchResult]:
    model = get_model(model_id)
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
        for pair, score in model.search(q, top_k=top_k)
    ]
