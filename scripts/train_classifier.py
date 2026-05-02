"""
Train the resolved-thread classifier from source-neutral threads.

Usage:
    python -m scripts.train_classifier tipofmyjoystick
    python -m scripts.train_classifier tipofmyjoystick --threads data/tipofmyjoystick/threads.jsonl
"""

import argparse
import re
from pathlib import Path

import yaml

from framework.classifier import BootstrapDataBuilder, ResolvedThreadClassifier
from framework.threads import iter_threads_jsonl


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train the resolved-thread classifier")
    p.add_argument("model", help="Model name, e.g. tipofmyjoystick")
    p.add_argument("--threads", help="Path to source-neutral threads.jsonl")
    p.add_argument("--output", help="Override output directory for classifier weights")
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--grad-accum", type=int, default=2)
    p.add_argument("--num-workers", type=int, default=4, help="DataLoader worker processes")
    p.add_argument("--no-bf16", action="store_true", help="Disable bf16 training on supported GPUs")
    p.add_argument("--no-tf32", action="store_true", help="Disable TF32 matmul on NVIDIA Ampere+ GPUs")
    p.add_argument("--limit", type=int, default=None, help="Only read the first N threads")
    p.add_argument(
        "--exclude-weak-answer",
        default="^removed,bad title,enter game title here,^not a game$,^solved$,^unsolved$,^unknown$,^meta$,^mod$",
        help="Comma-separated regex patterns for weak answers to ignore",
    )
    return p.parse_args()


def _is_excluded(value: str | None, patterns: list[str]) -> bool:
    if not value:
        return False
    return any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in patterns)


def main() -> None:
    args = parse_args()

    config_path = Path("models") / args.model / "config.yaml"
    if not config_path.exists():
        raise SystemExit(f"Config not found: {config_path}")
    config = yaml.safe_load(config_path.read_text())

    threads_path = Path(args.threads or f"data/{args.model}/threads.jsonl")
    if not threads_path.exists():
        raise SystemExit(f"Threads file not found: {threads_path}")

    output = args.output or f"models/{args.model}/resolved_thread_classifier"
    patterns = [p.strip() for p in args.exclude_weak_answer.split(",") if p.strip()]

    print(f"Loading threads from {threads_path}")
    threads = []
    total = 0
    skipped_weak_answer = 0
    for thread in iter_threads_jsonl(threads_path):
        total += 1
        if args.limit and total > args.limit:
            total -= 1
            break
        if _is_excluded(thread.weak_answer, patterns):
            thread.weak_answer = None
            thread.weak_status = None
            skipped_weak_answer += 1
        if thread.weak_answer:
            threads.append(thread)

    print(f"Threads total: {total:,}")
    print(f"Weak-answer threads: {len(threads):,}")
    print(f"Excluded weak answers: {skipped_weak_answer:,}")

    print("\nExtracting training examples...")
    examples = BootstrapDataBuilder().build(threads)
    pos = sum(1 for e in examples if e.label == 1)
    print(f"Examples: {len(examples):,} ({pos:,} positive, {len(examples) - pos:,} negative)")

    if not examples:
        raise SystemExit("No training examples extracted. Check weak answers and messages.")

    base_model = config["classifier"]["base_model"]
    print(f"\nFine-tuning {base_model} -> {output}")
    ResolvedThreadClassifier.train(
        examples=examples,
        output_path=output,
        base_model=base_model,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        dataloader_num_workers=args.num_workers,
        use_bf16=False if args.no_bf16 else None,
        use_tf32=not args.no_tf32,
    )
    print(f"\nClassifier saved to {output}")


if __name__ == "__main__":
    main()
