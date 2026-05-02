"""
Scrape a Reddit source into source-neutral threads.jsonl.

Usage:
    python -m scripts.scrape_threads tipofmyjoystick --output data/tipofmyjoystick/threads.jsonl
"""

import argparse
import asyncio
import json
from pathlib import Path

from framework.threads import thread_to_dict
from framework.scraper import ArcticShiftScraper


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Scrape Reddit threads through Arctic Shift")
    p.add_argument("subreddit", help="Subreddit name without r/")
    p.add_argument("--output", required=True, help="Output threads.jsonl path")
    p.add_argument("--after", type=int, default=0)
    p.add_argument("--before", type=int, default=None)
    p.add_argument("--request-delay", type=float, default=1.0)
    p.add_argument("--limit", type=int, default=None, help="Optional max threads for smoke tests")
    return p.parse_args()


async def scrape(args: argparse.Namespace) -> None:
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    async with ArcticShiftScraper(
        args.subreddit,
        after=args.after,
        before=args.before,
        request_delay=args.request_delay,
    ) as scraper:
        with output.open("w", encoding="utf-8", newline="\n") as f:
            count = 0
            async for thread in scraper.stream_threads():
                f.write(json.dumps(thread_to_dict(thread), ensure_ascii=False) + "\n")
                count += 1
                if count % 1000 == 0:
                    print(f"  {count:,} threads scraped...")
                if args.limit and count >= args.limit:
                    break


def main() -> None:
    args = parse_args()
    asyncio.run(scrape(args))
    print(f"Saved threads to {args.output}")


if __name__ == "__main__":
    main()
