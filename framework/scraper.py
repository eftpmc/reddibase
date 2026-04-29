"""
Arctic Shift API scraper base class.

Pulls all posts and their full comment threads for a given subreddit with no
flair filtering and no 1000-post limit. Pagination is cursor-based via the
`after` UTC timestamp returned from each batch.
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from typing import Any, Optional

import httpx

from framework.schema import Comment, Post

logger = logging.getLogger(__name__)

_BASE_URL = "https://arctic-shift.photon-reddit.com/api"
_POST_BATCH_SIZE = 100      # max per page for posts endpoint
_COMMENT_BATCH_SIZE = 100   # max per page for comments endpoint
_COMMENT_CONCURRENCY = 8    # parallel comment-fetch tasks
_MAX_BACKOFF = 60.0


class ArcticShiftScraper:
    """
    Streams all posts + full comment threads for a subreddit from Arctic Shift.

    Usage::

        async with ArcticShiftScraper("tipofmyjoystick") as scraper:
            async for post in scraper.stream_posts():
                process(post)

    Args:
        subreddit: Subreddit name without the r/ prefix.
        after: Earliest post creation timestamp (UTC seconds) to include.
               Defaults to 0 (full archive).
        before: Latest post creation timestamp (UTC seconds) to include.
                Defaults to now.
        request_delay: Minimum seconds to wait between post-page requests.
                       Arctic Shift is a volunteer service — be polite.
        max_retries: Number of times to retry a failed request before raising.
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
            headers={"User-Agent": "reddibase/0.1 (open-source identification model platform)"},
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def stream_posts(self) -> AsyncIterator[Post]:
        """
        Async generator that yields every Post (with comments) for the
        subreddit in ascending creation order.
        """
        sem = asyncio.Semaphore(_COMMENT_CONCURRENCY)
        cursor = self.after

        while True:
            batch = await self._fetch_post_page(cursor)
            if not batch:
                break

            tasks = [
                asyncio.create_task(self._enrich_with_comments(post, sem))
                for post in batch
            ]
            enriched = await asyncio.gather(*tasks)

            for post in enriched:
                yield post

            if len(batch) < _POST_BATCH_SIZE:
                break  # last page

            # Advance cursor past the last post in this batch.
            # +1 avoids re-fetching the boundary post on the next call.
            cursor = batch[-1].created_utc + 1
            await asyncio.sleep(self.request_delay)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _fetch_post_page(self, after_ts: int) -> list[Post]:
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
        return [_parse_post(raw) for raw in data.get("data", [])]

    async def _fetch_comment_page(
        self, post_id: str, after_ts: int = 0
    ) -> list[Comment]:
        params: dict[str, Any] = {
            "link_id": f"t3_{post_id}",
            "limit": _COMMENT_BATCH_SIZE,
            "sort": "asc",
            "sort_type": "created_utc",
        }
        if after_ts:
            params["after"] = after_ts
        data = await self._get(f"{_BASE_URL}/comments/search", params)
        return [_parse_comment(post_id, raw) for raw in data.get("data", [])]

    async def _fetch_all_comments(self, post_id: str) -> list[Comment]:
        """Paginate through all comments for a single post."""
        all_comments: list[Comment] = []
        cursor = 0

        while True:
            page = await self._fetch_comment_page(post_id, cursor)
            all_comments.extend(page)
            if len(page) < _COMMENT_BATCH_SIZE:
                break
            cursor = page[-1].created_utc + 1

        return all_comments

    async def _enrich_with_comments(
        self, post: Post, sem: asyncio.Semaphore
    ) -> Post:
        async with sem:
            try:
                post.comments = await self._fetch_all_comments(post.id)
            except Exception:
                logger.warning("Failed to fetch comments for post %s", post.id, exc_info=True)
        return post

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


# ------------------------------------------------------------------
# Raw JSON → dataclass parsers
# ------------------------------------------------------------------

def _parse_post(raw: dict[str, Any]) -> Post:
    return Post(
        id=raw["id"],
        subreddit=raw.get("subreddit", ""),
        title=raw.get("title", ""),
        body=raw.get("selftext", "") or "",
        author=raw.get("author", "[deleted]"),
        score=raw.get("score", 0),
        created_utc=int(raw.get("created_utc", 0)),
        flair=raw.get("link_flair_text") or raw.get("link_flair_css_class"),
        url=raw.get("full_link", f"https://reddit.com/r/{raw.get('subreddit', '')}/comments/{raw['id']}/"),
    )


def _parse_comment(post_id: str, raw: dict[str, Any]) -> Comment:
    return Comment(
        id=raw["id"],
        post_id=post_id,
        author=raw.get("author", "[deleted]"),
        body=raw.get("body", "") or "",
        score=raw.get("score", 0),
        created_utc=int(raw.get("created_utc", 0)),
        parent_id=raw.get("parent_id", f"t3_{post_id}"),
    )
