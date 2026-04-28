"""
Train the solved classifier for a model.

Steps:
  1. Scrape all posts (or load from cache).
  2. Extract bootstrap training examples from flaired posts.
  3. Fine-tune DistilBERT.
  4. Save weights to models/{model}/solved_classifier/.

Usage:
    python -m scripts.train_classifier tipofmyjoystick
    python -m scripts.train_classifier tipofmyjoystick --cache posts.pkl
"""

import argparse
import asyncio
import pickle
from pathlib import Path

import yaml

from framework.classifier import BootstrapDataBuilder, SolvedClassifier
from framework.scraper import ArcticShiftScraper


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train the solved classifier for a Reddibase model")
    p.add_argument("model", help="Model name, e.g. tipofmyjoystick")
    p.add_argument("--cache", help="Path to a .pkl of pre-scraped posts (skips scraping)")
    p.add_argument("--output", help="Override output directory for classifier weights")
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--grad-accum", type=int, default=2, help="Gradient accumulation steps (effective batch = batch-size × grad-accum)")
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

    output = args.output or f"models/{args.model}/solved_classifier"

    # ---- Step 1: posts ----
    if args.cache and Path(args.cache).exists():
        print(f"Loading posts from cache: {args.cache}")
        with open(args.cache, "rb") as f:
            posts = pickle.load(f)
    else:
        print(f"Scraping r/{config['subreddit']} (this may take a while)...")
        posts = asyncio.run(_scrape(config))
        if args.cache:
            with open(args.cache, "wb") as f:
                pickle.dump(posts, f)
            print(f"Cached {len(posts):,} posts → {args.cache}")

    flaired = [p for p in posts if p.flair]
    print(
        f"\nPosts total: {len(posts):,} | flaired (solved): {len(flaired):,} "
        f"({len(flaired) / len(posts) * 100:.1f}%)"
    )

    # ---- Step 2: training examples ----
    print("\nExtracting training examples...")
    builder = BootstrapDataBuilder()
    examples = builder.build(flaired)
    pos = sum(1 for e in examples if e.label == 1)
    print(f"Examples: {len(examples):,} ({pos:,} positive, {len(examples) - pos:,} negative)")

    if not examples:
        raise SystemExit("No training examples extracted — check that flaired posts have comments.")

    # ---- Step 3: train ----
    print(f"\nFine-tuning {config['classifier']['base_model']} → {output}")
    SolvedClassifier.train(
        examples=examples,
        output_path=output,
        base_model=config["classifier"]["base_model"],
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
    )
    print(f"\nClassifier saved to {output}")


if __name__ == "__main__":
    main()
