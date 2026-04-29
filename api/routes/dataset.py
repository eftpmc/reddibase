import csv
import io
import json

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from api.model_loader import get_model

router = APIRouter()

_FIELDS = ["post_id", "subreddit", "description", "answer", "flair", "confidence", "created_utc"]


def _pair_dict(p):
    return {f: getattr(p, f) for f in _FIELDS}


@router.get("/stats")
async def get_stats(model_id: str) -> dict:
    pairs = get_model(model_id)._pairs
    if not pairs:
        return {}

    confidences = [p.confidence for p in pairs]
    dates = [p.created_utc for p in pairs if p.created_utc]
    answer_counts: dict[str, int] = {}
    for p in pairs:
        key = (p.flair or p.answer or "").strip()
        if key:
            answer_counts[key] = answer_counts.get(key, 0) + 1

    top = sorted(answer_counts.items(), key=lambda x: -x[1])[:10]

    return {
        "total": len(pairs),
        "with_flair": sum(1 for p in pairs if p.flair),
        "without_flair": sum(1 for p in pairs if not p.flair),
        "unique_answers": len(answer_counts),
        "avg_confidence": round(sum(confidences) / len(confidences), 3),
        "min_date": min(dates) if dates else 0,
        "max_date": max(dates) if dates else 0,
        "top_answers": [{"answer": a, "count": c} for a, c in top],
    }


@router.get("/")
async def browse_dataset(
    model_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    q: str | None = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    max_confidence: float = Query(1.0, ge=0.0, le=1.0),
    date_from: int | None = Query(None),
    date_to: int | None = Query(None),
    source: str = Query("all"),  # "all", "flaired", "recovered"
) -> dict:
    pairs = get_model(model_id)._pairs

    if q:
        q_lower = q.lower()
        pairs = [p for p in pairs if q_lower in p.description.lower() or q_lower in (p.answer or "").lower()]
    if source == "flaired":
        pairs = [p for p in pairs if p.flair]
    elif source == "classifier":
        pairs = [p for p in pairs if not p.flair]
    if min_confidence > 0:
        pairs = [p for p in pairs if p.confidence >= min_confidence]
    if max_confidence < 1:
        pairs = [p for p in pairs if p.confidence <= max_confidence]
    if date_from:
        pairs = [p for p in pairs if p.created_utc and p.created_utc >= date_from]
    if date_to:
        pairs = [p for p in pairs if p.created_utc and p.created_utc <= date_to]

    total = len(pairs)
    start = (page - 1) * page_size
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_pair_dict(p) for p in pairs[start : start + page_size]],
    }


@router.get("/download")
async def download_dataset(
    model_id: str,
    fmt: str = Query("json", pattern="^(json|csv)$"),
) -> StreamingResponse:
    pairs = get_model(model_id)._pairs
    rows = [_pair_dict(p) for p in pairs]

    if fmt == "json":
        body = json.dumps(rows, indent=2)
        return StreamingResponse(
            io.StringIO(body),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={model_id}.json"},
        )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={model_id}.csv"},
    )
