"""
Canonicalize answers in an existing confirmed_pairs.jsonl artifact.

Use this to upgrade pairs created before framework.solution existed, without
rerunning classifier inference over the full threads file.
"""

import argparse
import json
from pathlib import Path

from framework.solution import extract_solution


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Canonicalize answers in confirmed_pairs.jsonl")
    p.add_argument("input", help="Input confirmed_pairs.jsonl")
    p.add_argument("--output", help="Output path. Defaults to overwriting input.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output or args.input)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    if not input_path.exists():
        raise SystemExit(f"Pairs file not found: {input_path}")

    count = 0
    methods: dict[str, int] = {}

    with input_path.open(encoding="utf-8") as src, tmp_path.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as dst:
        for line in src:
            raw = json.loads(line)
            answer_message = raw.get("answer_message_text") or raw.get("answer") or ""
            solution = extract_solution(answer_message, raw.get("weak_answer") or raw.get("flair"))

            raw["answer_message_text"] = answer_message
            raw["answer"] = solution.answer
            raw["canonical_answer"] = solution.answer
            raw["answer_extraction_method"] = solution.method

            dst.write(json.dumps(raw, ensure_ascii=False) + "\n")
            count += 1
            methods[solution.method] = methods.get(solution.method, 0) + 1

    tmp_path.replace(output_path)
    print(f"Canonicalized {count:,} pairs -> {output_path}")
    print("Methods:", methods)


if __name__ == "__main__":
    main()
