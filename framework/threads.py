import dataclasses
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from framework.schema import Message, Thread


def message_from_dict(data: dict[str, Any]) -> Message:
    return Message(
        id=data["id"],
        source_id=data.get("source_id", data["id"]),
        author_id=data.get("author_id"),
        body=data.get("body", ""),
        created_utc=data.get("created_utc", 0),
        parent_id=data.get("parent_id"),
        score=data.get("score", 0),
        metadata=data.get("metadata", {}),
    )


def thread_from_dict(data: dict[str, Any]) -> Thread:
    return Thread(
        id=data["id"],
        source=data.get("source", ""),
        source_id=data.get("source_id", data["id"]),
        community=data.get("community"),
        title=data.get("title", ""),
        body=data.get("body", ""),
        author_id=data.get("author_id"),
        created_utc=data.get("created_utc", 0),
        url=data.get("url", ""),
        score=data.get("score", 0),
        weak_answer=data.get("weak_answer"),
        weak_status=data.get("weak_status"),
        messages=[message_from_dict(m) for m in data.get("messages", [])],
        metadata=data.get("metadata", {}),
    )


def thread_to_dict(thread: Thread) -> dict[str, Any]:
    return dataclasses.asdict(thread)


def iter_threads_jsonl(path: str | Path) -> Iterator[Thread]:
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield thread_from_dict(json.loads(line))


def write_threads_jsonl(threads: Iterator[Thread], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for thread in threads:
            f.write(json.dumps(thread_to_dict(thread), ensure_ascii=False) + "\n")
