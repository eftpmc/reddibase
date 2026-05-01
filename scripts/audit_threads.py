"""
Audit a source-neutral threads.jsonl artifact before training.

Usage:
    python -m scripts.audit_threads tipofmyjoystick
    python -m scripts.audit_threads tipofmyjoystick --threads data/converted/tipofmyjoystick/threads.jsonl
"""

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from framework.threads import iter_threads_jsonl


DEFAULT_EXCLUDES = "^removed,bad title,enter game title here,^not a game$,^solved$,^unsolved$,^unknown$,^meta$,^mod$"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit a threads.jsonl artifact")
    p.add_argument("model", help="Model name, e.g. tipofmyjoystick")
    p.add_argument("--threads", help="Path to source-neutral threads.jsonl")
    p.add_argument("--limit", type=int, default=None, help="Only audit the first N threads")
    p.add_argument("--top", type=int, default=20, help="Number of top weak answers to print")
    p.add_argument("--output", help="Optional path to write audit JSON")
    p.add_argument(
        "--exclude-weak-answer",
        default=DEFAULT_EXCLUDES,
        help="Comma-separated regex patterns for non-answer weak labels",
    )
    return p.parse_args()


def _is_excluded(value: str | None, patterns: list[str]) -> bool:
    if not value:
        return False
    return any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in patterns)


def _iso(ts: int | None) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def main() -> None:
    args = parse_args()
    threads_path = Path(args.threads or f"data/converted/{args.model}/threads.jsonl")
    if not threads_path.exists():
        raise SystemExit(f"Threads file not found: {threads_path}")

    patterns = [p.strip() for p in args.exclude_weak_answer.split(",") if p.strip()]

    total = 0
    with_messages = 0
    empty_text = 0
    message_total = 0
    weak_answer_total = 0
    usable_weak_answer_total = 0
    excluded_weak_answer_total = 0
    first_created = None
    last_created = None
    source_counts: Counter[str] = Counter()
    community_counts: Counter[str] = Counter()
    weak_answers: Counter[str] = Counter()
    usable_weak_answers: Counter[str] = Counter()
    excluded_weak_answers: Counter[str] = Counter()
    message_counts: list[int] = []

    for thread in iter_threads_jsonl(threads_path):
        total += 1
        if args.limit and total > args.limit:
            total -= 1
            break

        source_counts[thread.source] += 1
        if thread.community:
            community_counts[thread.community] += 1

        created = thread.created_utc
        first_created = created if first_created is None else min(first_created, created)
        last_created = created if last_created is None else max(last_created, created)

        text = f"{thread.title or ''} {thread.body or ''}".strip()
        if not text:
            empty_text += 1

        msg_count = len(thread.messages)
        message_counts.append(msg_count)
        message_total += msg_count
        if msg_count:
            with_messages += 1

        if thread.weak_answer:
            weak_answer_total += 1
            weak_answers[thread.weak_answer] += 1
            if _is_excluded(thread.weak_answer, patterns):
                excluded_weak_answer_total += 1
                excluded_weak_answers[thread.weak_answer] += 1
            else:
                usable_weak_answer_total += 1
                usable_weak_answers[thread.weak_answer] += 1

        if total % 100000 == 0:
            print(f"  audited {total:,} threads...")

    sorted_message_counts = sorted(message_counts)

    def percentile(pct: float) -> int:
        if not sorted_message_counts:
            return 0
        idx = int((len(sorted_message_counts) - 1) * pct)
        return sorted_message_counts[idx]

    report = {
        "threads_path": str(threads_path),
        "threads": total,
        "sources": dict(source_counts.most_common()),
        "communities": dict(community_counts.most_common()),
        "first_created_utc": first_created,
        "first_created_iso": _iso(first_created),
        "last_created_utc": last_created,
        "last_created_iso": _iso(last_created),
        "empty_text_threads": empty_text,
        "threads_with_messages": with_messages,
        "messages": message_total,
        "messages_per_thread_avg": round(message_total / total, 3) if total else 0,
        "messages_per_thread_p50": percentile(0.50),
        "messages_per_thread_p90": percentile(0.90),
        "messages_per_thread_p99": percentile(0.99),
        "weak_answer_threads": weak_answer_total,
        "usable_weak_answer_threads": usable_weak_answer_total,
        "excluded_weak_answer_threads": excluded_weak_answer_total,
        "top_weak_answers": weak_answers.most_common(args.top),
        "top_usable_weak_answers": usable_weak_answers.most_common(args.top),
        "top_excluded_weak_answers": excluded_weak_answers.most_common(args.top),
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Saved audit to {output_path}")


if __name__ == "__main__":
    main()
