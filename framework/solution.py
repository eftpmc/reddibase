"""
Canonical solution extraction.

The resolved-thread classifier finds the comment that appears to solve a
thread. This module turns that comment, optionally helped by a weak source
label such as flair, into the shortest answer string we can safely store.
"""

import re
from dataclasses import dataclass
from typing import Optional

from rapidfuzz import fuzz

_SOLVED_PREFIX_RE = re.compile(
    r"^\s*(?:\[(?:solved|found)\]\s*)?(?:solved|found|answer(?:ed)?|identified)\s*[:-]\s*",
    re.IGNORECASE,
)
_LEADING_PHRASE_RE = re.compile(
    r"^\s*(?:"
    r"it'?s|it is|this is|that is|this was|that was|"
    r"sounds like|looks like|seems like|maybe|probably|"
    r"could be|might be|i think it'?s|i believe it'?s|"
    r"is it|was it|are you thinking of|you'?re thinking of|"
    r"the game is|game is|answer is"
    r")\s+",
    re.IGNORECASE,
)
_TRAILING_PHRASE_RE = re.compile(
    r"\s+(?:i think|maybe|probably|perhaps|if i remember correctly)\s*$",
    re.IGNORECASE,
)
_BRACKET_PREFIX_RE = re.compile(r"^\s*(?:\[[^\]]+\]\s*)+")
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_URL_RE = re.compile(r"https?://\S+")
_WHITESPACE_RE = re.compile(r"\s+")

_BAD_WEAK_ANSWERS = {
    "",
    "solved",
    "unsolved",
    "unknown",
    "removed",
    "not a game",
    "enter game title here",
    "meta",
    "mod",
}


@dataclass(frozen=True)
class ExtractedSolution:
    answer: str
    method: str


def extract_solution(
    answer_comment: str,
    weak_answer: Optional[str] = None,
) -> ExtractedSolution:
    """
    Return a canonical answer string from the selected answer comment.

    Weak answers are useful scaffolding when they overlap the answer comment,
    but they are cleaned and rejected when generic. This keeps TOMJ flairs
    helpful without making flair mandatory for future sources.
    """
    clean_weak = clean_solution_text(weak_answer or "")
    clean_comment = clean_solution_text(answer_comment)

    if clean_weak and _weak_answer_matches_comment(clean_weak, answer_comment):
        return ExtractedSolution(clean_weak, "weak_answer")

    if clean_comment:
        return ExtractedSolution(clean_comment, "answer_comment")

    return ExtractedSolution((answer_comment or weak_answer or "").strip(), "raw")


def clean_solution_text(text: str) -> str:
    text = _MARKDOWN_LINK_RE.sub(r"\1", text or "")
    text = _URL_RE.sub("", text)
    text = text.replace("&amp;", "&")
    text = _BRACKET_PREFIX_RE.sub("", text)
    text = _SOLVED_PREFIX_RE.sub("", text)
    text = _LEADING_PHRASE_RE.sub("", text)
    text = _TRAILING_PHRASE_RE.sub("", text)

    # Keep the first concise answer-like clause from conversational comments.
    parts = re.split(r"(?:\n|(?:\s+-\s+)|[.!?]|,?\s+(?:but|or maybe|not sure if)\s+)", text, maxsplit=1)
    text = parts[0]

    text = text.strip(" \t\r\n\"'`*_~:;-()[]{}")
    text = _WHITESPACE_RE.sub(" ", text).strip()

    if text.lower() in _BAD_WEAK_ANSWERS:
        return ""
    if len(text) > 80:
        return ""
    return _title_case_answer(text)


def _weak_answer_matches_comment(clean_weak: str, answer_comment: str) -> bool:
    if not clean_weak:
        return False
    comment = (answer_comment or "").lower()
    weak = clean_weak.lower()
    return weak in comment or fuzz.partial_ratio(weak, comment) >= 85


def _title_case_answer(text: str) -> str:
    if not text:
        return text
    if text.isupper() and len(text) > 3:
        return text.title()
    return text
