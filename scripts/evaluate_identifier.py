"""
Evaluate an identification model with leave-one-out answer retrieval.

For each sampled pair whose canonical answer appears at least twice, query with
that pair's description and check whether the top-k results contain another
pair with the same canonical answer.
"""

import argparse
import random
from collections import Counter, defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate identifier retrieval quality")
    p.add_argument("model", help="Model name, e.g. tipofmyjoystick")
    p.add_argument("--pairs", help="Path to confirmed_pairs.jsonl or exported pairs.jsonl")
    p.add_argument("--model-path", help="Identifier model directory")
    p.add_argument("--index-path", help="Identifier index/pairs directory")
    p.add_argument("--sample-size", type=int, default=5000)
    p.add_argument("--top-k", type=int, default=10)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--min-answer-count", type=int, default=2)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    from framework.embedder import IdentificationModel, _canonical_answer, _load_pairs

    pairs_path = Path(args.pairs or f"models/{args.model}/identification_model/pairs.jsonl")
    model_path = args.model_path or f"models/{args.model}/identification_model"
    index_path = args.index_path or model_path

    if not pairs_path.exists():
        raise SystemExit(f"Pairs file not found: {pairs_path}")

    pairs = _load_pairs(str(pairs_path))
    answer_counts = Counter(_canonical_answer(pair) for pair in pairs)
    eligible_indices = [
        idx
        for idx, pair in enumerate(pairs)
        if answer_counts[_canonical_answer(pair)] >= args.min_answer_count
    ]

    if not eligible_indices:
        raise SystemExit("No eligible pairs with repeated canonical answers.")

    random.seed(args.seed)
    sample_indices = random.sample(eligible_indices, min(args.sample_size, len(eligible_indices)))

    print(f"Pairs: {len(pairs):,}")
    print(f"Repeated-answer eligible pairs: {len(eligible_indices):,}")
    print(f"Sample size: {len(sample_indices):,}")
    print(f"Loading identifier from {model_path}")

    model = IdentificationModel(model_path, index_path).load()

    hit_at_1 = 0
    hit_at_k = 0
    reciprocal_ranks = []
    by_answer_hits: dict[str, list[int]] = defaultdict(list)
    misses = []

    for n, idx in enumerate(sample_indices, start=1):
        query_pair = pairs[idx]
        expected = _canonical_answer(query_pair)
        results = model.search(query_pair.description, top_k=args.top_k + 1)

        rank = None
        for result_rank, (candidate, _score) in enumerate(results, start=1):
            if candidate.source_id == query_pair.source_id:
                continue
            if _canonical_answer(candidate) == expected:
                rank = result_rank
                break

        if rank == 1:
            hit_at_1 += 1
        if rank is not None and rank <= args.top_k:
            hit_at_k += 1
            reciprocal_ranks.append(1.0 / rank)
            by_answer_hits[expected].append(1)
        else:
            reciprocal_ranks.append(0.0)
            by_answer_hits[expected].append(0)
            if len(misses) < 10:
                misses.append((query_pair, results[: min(args.top_k, len(results))]))

        if n % 500 == 0:
            print(f"  evaluated {n:,}/{len(sample_indices):,}...")

    total = len(sample_indices)
    print("\nMetrics")
    print(f"hit@1: {hit_at_1 / total:.3f}")
    print(f"hit@{args.top_k}: {hit_at_k / total:.3f}")
    print(f"mrr@{args.top_k}: {sum(reciprocal_ranks) / total:.3f}")

    answer_totals = {
        answer: len(values)
        for answer, values in by_answer_hits.items()
        if len(values) >= 5
    }
    weak_answers = sorted(
        (
            (sum(by_answer_hits[answer]) / count, count, answer)
            for answer, count in answer_totals.items()
        ),
        key=lambda item: (item[0], -item[1]),
    )[:10]
    if weak_answers:
        print("\nLowest repeated-answer hit rates in sample")
        for rate, count, answer in weak_answers:
            print(f"{rate:.2f} ({count} queries): {answer}")

    if misses:
        print("\nExample misses")
        for query_pair, results in misses:
            print(f"\nExpected: {_canonical_answer(query_pair)}")
            print(f"Query: {query_pair.description[:220].replace(chr(10), ' ')}")
            for candidate, score in results[:5]:
                print(f"  {score:.3f} | {_canonical_answer(candidate)} | {candidate.source_id}")


if __name__ == "__main__":
    main()
