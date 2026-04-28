import csv
import io
import json

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from api.model_loader import get_model

router = APIRouter()

_FIELDS = ["post_id", "description", "answer", "flair", "confidence", "created_utc"]


def _pair_dict(p):
    return {f: getattr(p, f) for f in _FIELDS}


@router.get("/")
async def browse_dataset(
    model_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    q: str | None = Query(None),
) -> dict:
    pairs = get_model(model_id)._pairs

    if q:
        q_lower = q.lower()
        pairs = [
            p for p in pairs
            if q_lower in p.description.lower() or q_lower in (p.answer or "").lower()
        ]

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
