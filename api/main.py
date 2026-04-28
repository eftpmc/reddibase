from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import dataset, models, search

app = FastAPI(title="Reddibase API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(models.router, prefix="/models", tags=["models"])
app.include_router(dataset.router, prefix="/models/{model_id}/dataset", tags=["dataset"])
app.include_router(search.router, prefix="/models/{model_id}/search", tags=["search"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
