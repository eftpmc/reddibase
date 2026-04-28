from fastapi import APIRouter

from api.model_loader import list_configs

router = APIRouter()


@router.get("/")
async def list_models() -> list[dict]:
    return [
        {
            "id": c["name"],
            "display_name": c.get("display_name", c["name"]),
            "description": c.get("description", ""),
            "subreddit": c["subreddit"],
            "hf_repo": c["hf_repo"],
            "confirmed_pairs": c.get("stats", {}).get("confirmed_pairs", 0),
        }
        for c in list_configs()
    ]
