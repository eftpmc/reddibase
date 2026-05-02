"""
Identification model pipeline.

Fine-tunes a Sentence Transformer so that descriptions of the same answer land
close together in vector space, then builds a FAISS index over the full
confirmed-pair set for fast nearest-neighbour retrieval at inference time.

The FAISS index is static and lives on disk alongside the encoder. It is only
rebuilt when new confirmed pairs are added — never at query time.
"""

import dataclasses
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Optional

import faiss
import numpy as np

from framework.schema import ConfirmedPair

_INDEX_FILE = "index.faiss"
_PAIRS_FILE = "pairs.jsonl"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class IdentificationModel:
    """
    Fine-tuned Sentence Transformer + FAISS index for vague-description retrieval.

    Load from disk::

        model = IdentificationModel(encoder_path, index_path).load()
        results = model.search("knight game ps1 collect gems", top_k=10)

    Train from scratch::

        model = IdentificationModel.train(confirmed_pairs, output_path="models/tipofmyjoystick/identification_model")
    """

    def __init__(self, model_path: str, index_path: str) -> None:
        self.model_path = model_path
        self.index_path = index_path
        self._encoder = None
        self._index: Optional[faiss.Index] = None
        self._pairs: list[ConfirmedPair] = []

    def load(self) -> "IdentificationModel":
        from sentence_transformers import SentenceTransformer

        self._encoder = SentenceTransformer(self.model_path)
        self._index = faiss.read_index(os.path.join(self.index_path, _INDEX_FILE))
        self._pairs = _load_pairs(os.path.join(self.index_path, _PAIRS_FILE))
        return self

    def search(self, query: str, top_k: int = 10) -> list[tuple[ConfirmedPair, float]]:
        """Return top_k (pair, cosine_similarity) tuples for the query."""
        assert self._encoder and self._index, "Call load() first"

        vec = self._encoder.encode([query], normalize_embeddings=True).astype(np.float32)
        scores, indices = self._index.search(vec, top_k)

        return [
            (self._pairs[idx], float(score))
            for score, idx in zip(scores[0], indices[0])
            if 0 <= idx < len(self._pairs)
        ]

    def rebuild_index(self, pairs: list[ConfirmedPair]) -> None:
        """
        Re-encode pairs and rebuild the FAISS index in place.
        Call this when new confirmed pairs are added without retraining the encoder.
        """
        assert self._encoder, "Call load() first"
        _build_and_save_index(self._encoder, pairs, self.index_path)
        self._index = faiss.read_index(os.path.join(self.index_path, _INDEX_FILE))
        self._pairs = pairs

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    @classmethod
    def train(
        cls,
        pairs: list[ConfirmedPair],
        base_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        output_path: str = "models/encoder",
        num_epochs: int = 3,
        batch_size: int = 32,
        warmup_ratio: float = 0.1,
    ) -> "IdentificationModel":
        from sentence_transformers import SentenceTransformer, losses
        from torch.utils.data import DataLoader

        examples = _build_training_examples(pairs)
        if not examples:
            raise ValueError("No training examples — need confirmed pairs with shared canonical answers")

        print(f"Training examples: {len(examples):,}")

        encoder = SentenceTransformer(base_model)
        dataloader = DataLoader(examples, shuffle=True, batch_size=batch_size)
        loss_fn = losses.MultipleNegativesRankingLoss(encoder)
        warmup_steps = int(len(dataloader) * num_epochs * warmup_ratio)

        encoder.fit(
            train_objectives=[(dataloader, loss_fn)],
            epochs=num_epochs,
            warmup_steps=warmup_steps,
            output_path=output_path,
            show_progress_bar=True,
        )

        _build_and_save_index(encoder, pairs, output_path)
        return cls(output_path, output_path).load()

    def push_to_hub(self, repo_id: str) -> None:
        """Push encoder weights to Hugging Face Hub. Index artifacts go to the paired dataset repo."""
        assert self._encoder, "Call load() first"
        self._encoder.push_to_hub(repo_id)


# ---------------------------------------------------------------------------
# Training data construction
# ---------------------------------------------------------------------------

def _canonical_answer(pair: ConfirmedPair) -> str:
    """
    The best available canonical answer key for grouping pairs by game.
    Newer pair artifacts store canonical_answer directly. Older artifacts fall
    back to answer, then weak/flair text for compatibility.
    """
    return (pair.canonical_answer or pair.answer or pair.weak_answer or pair.flair).strip().lower()


def _build_training_examples(pairs: list[ConfirmedPair]) -> list:
    """
    Build (anchor, positive) pairs for MultipleNegativesRankingLoss.

    Two sources:

    1. Description–description pairs: when the same game appears in multiple
       confirmed posts, pair those descriptions together. This directly optimises
       for the retrieval task (query description → similar description in index).
       Consecutive pairing avoids O(n²) explosion for popular titles.

    2. Description–answer pairs: for every confirmed pair, treat the canonical
       answer text as a positive for the description. This gives the encoder
       signal even for games with only one confirmed post (the majority).
    """
    from sentence_transformers import InputExample

    groups: dict[str, list[str]] = defaultdict(list)
    for pair in pairs:
        groups[_canonical_answer(pair)].append(pair.description)

    examples = []

    for descriptions in groups.values():
        if len(descriptions) >= 2:
            for i in range(len(descriptions) - 1):
                examples.append(InputExample(texts=[descriptions[i], descriptions[i + 1]]))

    for pair in pairs:
        examples.append(InputExample(texts=[pair.description, _canonical_answer(pair)]))

    return examples


# ---------------------------------------------------------------------------
# FAISS index helpers
# ---------------------------------------------------------------------------

def _build_and_save_index(
    encoder,
    pairs: list[ConfirmedPair],
    output_path: str,
) -> None:
    descriptions = [p.description for p in pairs]

    print(f"Encoding {len(descriptions):,} descriptions...")
    embeddings = encoder.encode(
        descriptions,
        batch_size=64,
        normalize_embeddings=True,
        show_progress_bar=True,
        convert_to_numpy=True,
    ).astype(np.float32)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # inner product == cosine sim on L2-normalised vectors
    index.add(embeddings)

    Path(output_path).mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, os.path.join(output_path, _INDEX_FILE))

    with open(os.path.join(output_path, _PAIRS_FILE), "w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(dataclasses.asdict(pair)) + "\n")

    print(f"Index: {len(pairs):,} vectors, dim={dim} → {output_path}/")


def _load_pairs(path: str) -> list[ConfirmedPair]:
    pairs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            raw = json.loads(line)
            if "thread_id" not in raw:
                raw = {
                    **raw,
                    "thread_id": raw.get("post_id", ""),
                    "source": raw.get("source") or "reddit",
                    "source_id": raw.get("post_id", ""),
                    "community": raw.get("subreddit"),
                    "answer_message_id": raw.get("answer_comment_id", ""),
                    "weak_answer": raw.get("flair"),
                }
            pairs.append(ConfirmedPair(**raw))
    return pairs
