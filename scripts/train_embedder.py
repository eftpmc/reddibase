"""
Fine-tune the identification model and build the FAISS index.

Reads confirmed_pairs.jsonl produced by build_dataset.py and trains a
Sentence Transformer encoder, then encodes all descriptions and saves the
FAISS index alongside the encoder weights.

Usage:
    python -m scripts.train_embedder tipofmyjoystick
    python -m scripts.train_embedder tipofmyjoystick --pairs custom_pairs.jsonl
"""

import argparse
from pathlib import Path

import yaml

from framework.embedder import IdentificationModel
from framework.embedder import _load_pairs


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train the identification model for a Reddibase model")
    p.add_argument("model", help="Model name, e.g. tipofmyjoystick")
    p.add_argument("--pairs", help="Path to confirmed_pairs.jsonl (default: models/{model}/confirmed_pairs.jsonl)")
    p.add_argument("--output", help="Override output directory for encoder weights + FAISS index")
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch-size", type=int, default=32)
    return p.parse_args()


def main() -> None:
    args = parse_args()

    config_path = Path("models") / args.model / "config.yaml"
    if not config_path.exists():
        raise SystemExit(f"Config not found: {config_path}")
    config = yaml.safe_load(config_path.read_text())

    pairs_path = args.pairs or f"models/{args.model}/confirmed_pairs.jsonl"
    output = args.output or f"models/{args.model}/identification_model"
    base_encoder = config["identification_model"]["base_encoder"]

    if not Path(pairs_path).exists():
        raise SystemExit(
            f"Pairs file not found: {pairs_path}\n"
            "Run scripts/build_dataset.py first."
        )

    print(f"Loading confirmed pairs from {pairs_path}")
    pairs = _load_pairs(pairs_path)

    unique_answers = len(
        {(p.canonical_answer or p.answer or p.weak_answer or "").lower() for p in pairs}
    )
    print(f"Pairs: {len(pairs):,} | unique answers: {unique_answers:,}")

    if unique_answers < 10:
        raise SystemExit("Too few unique answers to train meaningfully — need more confirmed pairs.")

    print(f"\nFine-tuning {base_encoder} → {output}")
    IdentificationModel.train(
        pairs=pairs,
        base_model=base_encoder,
        output_path=output,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
    )

    print(f"\nDone. Encoder + index saved → {output}/")
    print("Next: wire the model into api/routes/search.py")


if __name__ == "__main__":
    main()
