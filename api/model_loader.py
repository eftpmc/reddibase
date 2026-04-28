"""
Centralized model loading. Downloads encoder + artifacts from HF Hub on first
request, caches locally, and returns a loaded IdentificationModel.
"""

import logging
from pathlib import Path

import yaml
from fastapi import HTTPException
from huggingface_hub import hf_hub_download

from framework.embedder import IdentificationModel

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(".cache/models")
_model_cache: dict[str, IdentificationModel] = {}


def load_config(model_id: str) -> dict:
    path = Path(f"models/{model_id}/config.yaml")
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    with open(path) as f:
        return yaml.safe_load(f)


def list_configs() -> list[dict]:
    configs = []
    for config_path in sorted(Path("models").glob("*/config.yaml")):
        with open(config_path) as f:
            configs.append(yaml.safe_load(f))
    return configs


def get_model(model_id: str) -> IdentificationModel:
    if model_id in _model_cache:
        return _model_cache[model_id]

    config = load_config(model_id)
    hf_repo = config["hf_repo"]

    cache_dir = _CACHE_DIR / model_id
    cache_dir.mkdir(parents=True, exist_ok=True)

    try:
        hf_hub_download(repo_id=hf_repo, filename="index.faiss", local_dir=str(cache_dir))
        hf_hub_download(repo_id=hf_repo, filename="pairs.jsonl", local_dir=str(cache_dir))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Failed to download model '{model_id}': {exc}")

    logger.info("Loading model %s from %s", model_id, hf_repo)
    model = IdentificationModel(hf_repo, str(cache_dir)).load()
    _model_cache[model_id] = model
    return model
