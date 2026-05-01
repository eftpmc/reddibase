"""
Arctic Shift source adapter.

Streams source-neutral Thread objects for a subreddit. Reddit-specific fields
are contained in metadata; downstream classifier/identifier code only consumes
Thread and Message.
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from typing import Any, Optional

import httpx

from framework.schema import Message, Thread

logger = logging.getLogger(__name__)

_BASE_URL = "https://arctic-shift.photon-reddit.com/api"
_POST_BATCH_SIZE = 100
_COMMENT_BATCH_SIZE = 100
_COMMENT_CONCURRENCY = 4
_MAX_BACKOFF = 60.0


class ArcticShiftScraper:
    """
    Streams Reddit submissions + full comment threads as source-neutral Thread
    objects from Arctic Shift.
    """

    def __init__(
        self,
        subreddit: str,
        after: int = 0,
        before: Optional[int] = None,
        request_delay: float = 1.0,
        max_retries: int = 8,
    ) -> None:
        self.subreddit = subreddit
        self.after = after
        self.before = before or int(time.time())
        self.request_delay = request_delay
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "ArcticShiftScraper":
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={"User-Agent": "reddibase/0.1 (answer extraction research)"},
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def stream_threads(self) -> AsyncIterator[Thread]:
        """Yield every thread in ascending creation order."""
        sem = asyncio.Semaphore(_COMMENT_CONCURRENCY)
        cursor = self.after

        while True:
            batch = await self._fetch_thread_page(cursor)
            if not batch:
                break

            tasks = [
                asyncio.create_task(self._enrich_with_messages(thread, sem))
                for thread in batch
            ]
            enriched = await asyncio.gather(*tasks)

            for thread in enriched:
                yield thread

            if len(batch) < _POST_BATCH_SIZE:
                break

            cursor = batch[-1].created_utc + 1
            await asyncio.sleep(self.request_delay)

    async def _fetch_thread_page(self, after_ts: int) -> list[Thread]:
        params: dict[str, Any] = {
            "subreddit": self.subreddit,
            "before": self.before,
            "limit": _POST_BATCH_SIZE,
            "sort": "asc",
            "sort_type": "created_utc",
        }
        if after_ts:
            params["after"] = after_ts
        data = await self._get(f"{_BASE_URL}/posts/search", params)
        return [_parse_thread(raw) for raw in data.get("data", [])]

    async def _fetch_message_page(
        self, thread_source_id: str, after_ts: int = 0
    ) -> list[Message]:
        params: dict[str, Any] = {
            "link_id": f"t3_{thread_source_id}",
            "limit": _COMMENT_BATCH_SIZE,
            "sort": "asc",
            "sort_type": "created_utc",
        }
        if after_ts:
            params["after"] = after_ts
        data = await self._get(f"{_BASE_URL}/comments/search", params)
        return [_parse_message(thread_source_id, raw) for raw in data.get("data", [])]

    async def _fetch_all_messages(self, thread_source_id: str) -> list[Message]:
        all_messages: list[Message] = []
        cursor = 0

        while True:
            page = await self._fetch_message_page(thread_source_id, cursor)
            all_messages.extend(page)
            if len(page) < _COMMENT_BATCH_SIZE:
                break
            cursor = page[-1].created_utc + 1

        return all_messages

    async def _enrich_with_messages(
        self, thread: Thread, sem: asyncio.Semaphore
    ) -> Thread:
        async with sem:
            try:
                thread.messages = await self._fetch_all_messages(thread.source_id)
            except Exception:
                logger.warning(
                    "Failed to fetch messages for thread %s",
                    thread.source_id,
                    exc_info=True,
                )
        return thread

    async def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        assert self._client is not None, "Use ArcticShiftScraper as an async context manager"

        backoff = 2.0
        for attempt in range(self.max_retries):
            try:
                response = await self._client.get(url, params=params)

                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", backoff))
                    logger.warning("Rate limited; sleeping %.1fs", retry_after)
                    await asyncio.sleep(retry_after)
                    backoff = min(backoff * 2, _MAX_BACKOFF)
                    continue

                if 500 <= response.status_code < 600:
                    if attempt == self.max_retries - 1:
                        response.raise_for_status()
                    logger.warning(
                        "Server error %d on attempt %d/%d; retrying in %.1fs",
                        response.status_code,
                        attempt + 1,
                        self.max_retries,
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, _MAX_BACKOFF)
                    continue

                response.raise_for_status()
                return response.json()

            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt == self.max_retries - 1:
                    raise
                logger.warning(
                    "Request failed on attempt %d/%d; retrying in %.1fs",
                    attempt + 1,
                    self.max_retries,
                    backoff,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF)

        raise RuntimeError(f"Exhausted {self.max_retries} retries for {url}")


def _parse_thread(raw: dict[str, Any]) -> Thread:
    source_id = raw["id"]
    subreddit = raw.get("subreddit", "")
    weak_answer = raw.get("link_flair_text") or raw.get("link_flair_css_class")
    return Thread(
        id=f"reddit:{subreddit}:{source_id}",
        source="reddit",
        source_id=source_id,
        community=subreddit,
        title=raw.get("title", ""),
        body=raw.get("selftext", "") or "",
        author_id=raw.get("author", "[deleted]"),
        score=raw.get("score", 0),
        created_utc=int(raw.get("created_utc", 0)),
        url=raw.get(
            "full_link",
            f"https://reddit.com/r/{subreddit}/comments/{source_id}/",
        ),
        weak_answer=weak_answer,
        weak_status="answered" if weak_answer else None,
        metadata={
            "subreddit": subreddit,
            "raw_flair": weak_answer,
            "permalink": raw.get("permalink"),
        },
    )


def _parse_message(thread_source_id: str, raw: dict[str, Any]) -> Message:
    source_id = raw["id"]
    return Message(
        id=f"reddit-comment:{source_id}",
        source_id=source_id,
        author_id=raw.get("author", "[deleted]"),
        body=raw.get("body", "") or "",
        score=raw.get("score", 0),
        created_utc=int(raw.get("created_utc", 0)),
        parent_id=raw.get("parent_id", f"t3_{thread_source_id}"),
        metadata={
            "thread_source_id": thread_source_id,
            "link_id": raw.get("link_id"),
        },
    )
