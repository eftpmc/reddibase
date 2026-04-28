from fastapi import FastAPI

from api.routes import dataset, models, search

app = FastAPI(title="Reddibase API", version="0.1.0")

app.include_router(models.router, prefix="/models", tags=["models"])
app.include_router(dataset.router, prefix="/models/{model_id}/dataset", tags=["dataset"])
app.include_router(search.router, prefix="/models/{model_id}/search", tags=["search"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
