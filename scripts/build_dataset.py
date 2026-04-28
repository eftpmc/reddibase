"""
Run the trained classifier over all posts and emit confirmed (description, answer) pairs.

Steps:
  1. Load posts from cache or scrape fresh.
  2. Load the trained SolvedClassifier.
  3. For each post, predict (is_solved, answer_comment, confidence).
  4. Write pairs above the confidence threshold to a .jsonl file.

Usage:
    python -m scripts.build_dataset tipofmyjoystick --cache posts.pkl
    python -m scripts.build_dataset tipofmyjoystick --cache posts.pkl --output dataset.jsonl
"""

import argparse
import asyncio
import dataclasses
import json
import pickle
from pathlib import Path

import yaml

from framework.classifier import SolvedClassifier
from framework.scraper import ArcticShiftScraper


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build confirmed-pairs dataset for a Reddibase model")
    p.add_argument("model", help="Model name, e.g. tipofmyjoystick")
    p.add_argument("--cache", help="Path to a .pkl of pre-scraped posts (skips scraping)")
    p.add_argument("--output", help="Override output .jsonl path")
    p.add_argument("--classifier", help="Override classifier weights directory")
    p.add_argument("--threshold", type=float, default=None, help="Override confidence threshold from config")
    return p.parse_args()


async def _scrape(config: dict) -> list:
    posts = []
    scraper_cfg = config.get("scraper", {})

    async with ArcticShiftScraper(
        subreddit=config["subreddit"],
        after=scraper_cfg.get("after", 0),
        request_delay=scraper_cfg.get("request_delay", 1.0),
    ) as scraper:
        async for post in scraper.stream_posts():
            posts.append(post)
            if len(posts) % 500 == 0:
                print(f"  {len(posts):,} posts collected...")

    return posts


def main() -> None:
    args = parse_args()

    config_path = Path("models") / args.model / "config.yaml"
    if not config_path.exists():
        raise SystemExit(f"Config not found: {config_path}")
    config = yaml.safe_load(config_path.read_text())

    classifier_path = args.classifier or f"models/{args.model}/solved_classifier"
    output_path = args.output or f"models/{args.model}/confirmed_pairs.jsonl"
    threshold = args.threshold or config["classifier"].get("confidence_threshold", 0.80)

    # ---- posts ----
    if args.cache and Path(args.cache).exists():
        print(f"Loading posts from cache: {args.cache}")
        with open(args.cache, "rb") as f:
            posts = pickle.load(f)
    else:
        print(f"Scraping r/{config['subreddit']}...")
        posts = asyncio.run(_scrape(config))
        if args.cache:
            with open(args.cache, "wb") as f:
                pickle.dump(posts, f)

    print(f"Posts: {len(posts):,} | threshold: {threshold}")

    # ---- classifier ----
    print(f"Loading classifier from {classifier_path}")
    clf = SolvedClassifier(classifier_path).load()

    # ---- inference ----
    confirmed = []
    low_confidence = 0

    for i, post in enumerate(posts):
        if i % 1000 == 0:
            print(f"  {i:,}/{len(posts):,} processed, {len(confirmed):,} confirmed so far...")

        is_solved, answer, confidence = clf.predict(post)
        if is_solved and confidence >= threshold:
            confirmed.append(clf.to_confirmed_pair(post, answer, confidence))
        else:
            low_confidence += 1

    print(f"\nConfirmed: {len(confirmed):,} | below threshold: {low_confidence:,}")

    # ---- write output ----
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for pair in confirmed:
            f.write(json.dumps(dataclasses.asdict(pair)) + "\n")

    print(f"Dataset saved → {output_path}")


if __name__ == "__main__":
    main()
