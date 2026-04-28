from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Comment:
    id: str
    post_id: str
    author: str
    body: str
    score: int
    created_utc: int
    parent_id: str  # either post fullname (t3_xxx) or parent comment fullname (t1_xxx)
    is_op_reply: bool = False  # True if OP replied to this comment's parent thread


@dataclass
class Post:
    id: str
    subreddit: str
    title: str
    body: str
    author: str
    score: int
    created_utc: int
    flair: Optional[str]
    url: str
    comments: list[Comment] = field(default_factory=list)


@dataclass
class ConfirmedPair:
    """A confirmed (description → answer) pair extracted from a solved post."""
    post_id: str
    subreddit: str
    description: str         # post title + body
    answer: str              # winning comment body
    answer_comment_id: str
    confidence: float        # classifier confidence score
    flair: Optional[str] = None  # original post flair when present (canonical answer for tipofmyjoystick = game name)
    platform: Optional[str] = None
    year: Optional[int] = None
    created_utc: int = 0
