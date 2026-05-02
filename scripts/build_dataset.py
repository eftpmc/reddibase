"""
Run the resolved-thread classifier over threads and emit confirmed pairs.

Usage:
    python -m scripts.build_dataset tipofmyjoystick
    python -m scripts.build_dataset tipofmyjoystick --threads data/tipofmyjoystick/threads.jsonl
"""

import argparse
import dataclasses
import json
from pathlib import Path

import yaml

from framework.classifier import ResolvedThreadClassifier
from framework.threads import iter_threads_jsonl


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract confirmed answer pairs from threads")
    p.add_argument("model", help="Model name, e.g. tipofmyjoystick")
    p.add_argument("--threads", help="Path to source-neutral threads.jsonl")
    p.add_argument("--output", help="Override output confirmed_pairs.jsonl path")
    p.add_argument("--classifier", help="Override classifier weights directory")
    p.add_argument("--threshold", type=float, default=None)
    p.add_argument("--limit", type=int, default=None, help="Only process the first N threads")
    p.add_argument("--thread-batch-size", type=int, default=128, help="Threads to score per classifier call")
    p.add_argument("--candidate-batch-size", type=int, default=512, help="Candidate messages per GPU/CPU batch")
    p.add_argument("--max-length", type=int, default=None, help="Classifier token length for extraction")
    p.add_argument(
        "--amp-dtype",
        choices=["auto", "bf16", "fp16", "none"],
        default="auto",
        help="Mixed-precision dtype for CUDA classifier inference",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    config_path = Path("models") / args.model / "config.yaml"
    if not config_path.exists():
        raise SystemExit(f"Config not found: {config_path}")
    config = yaml.safe_load(config_path.read_text())

    threads_path = Path(args.threads or f"data/{args.model}/threads.jsonl")
    if not threads_path.exists():
        raise SystemExit(f"Threads file not found: {threads_path}")

    classifier_path = args.classifier or f"models/{args.model}/resolved_thread_classifier"
    output_path = Path(args.output or f"models/{args.model}/confirmed_pairs.jsonl")
    threshold = args.threshold or config["classifier"].get("confidence_threshold", 0.80)

    print(f"Loading classifier from {classifier_path}")
    clf = ResolvedThreadClassifier(classifier_path).load()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    processed = 0
    confirmed = 0
    below_threshold = 0

    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        batch = []

        def flush_batch() -> None:
            nonlocal confirmed, below_threshold
            if not batch:
                return
            predictions = clf.predict_batch(
                batch,
                batch_size=args.candidate_batch_size,
                max_length=args.max_length,
                amp_dtype=args.amp_dtype,
            )
            for thread, (is_solved, answer, confidence) in zip(batch, predictions):
                if is_solved and answer and confidence >= threshold:
                    pair = clf.to_confirmed_pair(thread, answer, confidence)
                    f.write(json.dumps(dataclasses.asdict(pair), ensure_ascii=False) + "\n")
                    confirmed += 1
                else:
                    below_threshold += 1
            batch.clear()

        for thread in iter_threads_jsonl(threads_path):
            if args.limit and processed >= args.limit:
                break
            if processed % 1000 == 0:
                print(f"  {processed:,} processed, {confirmed:,} confirmed...")

            batch.append(thread)
            processed += 1
            if len(batch) >= args.thread_batch_size:
                flush_batch()

        flush_batch()

    print(f"\nProcessed: {processed:,}")
    print(f"Confirmed: {confirmed:,}")
    print(f"Below threshold/no answer: {below_threshold:,}")
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    main()
