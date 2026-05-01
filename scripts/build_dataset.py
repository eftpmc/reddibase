"""
Run the resolved-thread classifier over threads and emit confirmed pairs.

Usage:
    python -m scripts.build_dataset tipofmyjoystick
    python -m scripts.build_dataset tipofmyjoystick --threads data/converted/tipofmyjoystick/threads.jsonl
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
    return p.parse_args()


def main() -> None:
    args = parse_args()

    config_path = Path("models") / args.model / "config.yaml"
    if not config_path.exists():
        raise SystemExit(f"Config not found: {config_path}")
    config = yaml.safe_load(config_path.read_text())

    threads_path = Path(args.threads or f"data/converted/{args.model}/threads.jsonl")
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
        for thread in iter_threads_jsonl(threads_path):
            if args.limit and processed >= args.limit:
                break
            if processed % 1000 == 0:
                print(f"  {processed:,} processed, {confirmed:,} confirmed...")

            is_solved, answer, confidence = clf.predict(thread)
            if is_solved and answer and confidence >= threshold:
                pair = clf.to_confirmed_pair(thread, answer, confidence)
                f.write(json.dumps(dataclasses.asdict(pair), ensure_ascii=False) + "\n")
                confirmed += 1
            else:
                below_threshold += 1

            processed += 1

    print(f"\nProcessed: {processed:,}")
    print(f"Confirmed: {confirmed:,}")
    print(f"Below threshold/no answer: {below_threshold:,}")
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    main()
