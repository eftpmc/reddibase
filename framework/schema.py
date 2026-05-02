from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Message:
    """A source-neutral reply/message inside a human-solved thread."""

    id: str
    source_id: str
    author_id: Optional[str]
    body: str
    created_utc: int
    parent_id: Optional[str] = None
    score: float = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class Thread:
    """A source-neutral discussion thread that may contain a resolved answer."""

    id: str
    source: str
    source_id: str
    community: Optional[str]
    title: str
    body: str
    author_id: Optional[str]
    created_utc: int
    url: str = ""
    score: float = 0
    weak_answer: Optional[str] = None
    weak_status: Optional[str] = None
    messages: list[Message] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class ConfirmedPair:
    """A confirmed (description -> answer) pair extracted from a solved thread."""

    thread_id: str
    source: str
    source_id: str
    community: Optional[str]
    description: str
    answer: str
    answer_message_id: str
    confidence: float
    weak_answer: Optional[str] = None
    canonical_answer: Optional[str] = None
    answer_message_text: Optional[str] = None
    answer_extraction_method: Optional[str] = None
    created_utc: int = 0
    platform: Optional[str] = None
    year: Optional[int] = None

    # Temporary aliases for current API/UI artifact compatibility. New pipeline
    # code should prefer thread_id/source_id/community/weak_answer.
    post_id: Optional[str] = None
    subreddit: Optional[str] = None
    answer_comment_id: Optional[str] = None
    flair: Optional[str] = None
