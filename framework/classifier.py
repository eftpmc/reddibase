"""
Solved-post classifier.

Bootstrap labels come from the flair-as-answer strategy: any post with a flair
is solved (flair text = game name = answer); no flair = unsolved.

The classifier learns comment-thread patterns (OP confirmation language, upvote
signals, etc.) — not the flair itself — so it can identify solved posts that OP
never flaired.
"""

import random
from dataclasses import dataclass
from typing import Optional

from rapidfuzz import fuzz

from framework.schema import Comment, ConfirmedPair, Post


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def mark_op_replies(post: Post) -> None:
    """
    Annotates each Comment with is_op_reply=True when OP directly replied to it.
    Mutates in place; safe to call multiple times.
    """
    op = post.author
    if op in ("[deleted]", "AutoModerator", ""):
        return

    # Set of fullnames (t1_{id}) that OP replied to
    op_targets = {
        c.parent_id
        for c in post.comments
        if c.author == op and c.parent_id.startswith("t1_")
    }

    for comment in post.comments:
        comment.is_op_reply = f"t1_{comment.id}" in op_targets


def get_op_reply(post: Post, comment: Comment) -> Optional[Comment]:
    """Return OP's direct reply to this comment, if one exists."""
    for c in post.comments:
        if c.author == post.author and c.parent_id == f"t1_{comment.id}":
            return c
    return None


def find_answer_comment(post: Post, flair_text: str) -> Optional[Comment]:
    """
    Best-effort identification of the answer comment for a solved post.

    Priority:
    1. High fuzzy match to flair_text AND OP replied to it.
    2. High fuzzy match to flair_text alone.
    3. Highest-upvoted comment OP replied to (flair match unavailable).
    """
    mark_op_replies(post)

    candidates = [
        c for c in post.comments
        if c.author not in ("[deleted]", "AutoModerator", post.author, "")
        and c.body not in ("[deleted]", "[removed]", "")
    ]
    if not candidates:
        return None

    scored = sorted(
        [(c, fuzz.partial_ratio(flair_text.lower(), c.body.lower())) for c in candidates],
        key=lambda x: (x[1], x[0].score),
        reverse=True,
    )

    for comment, score in scored:
        if score >= 60 and comment.is_op_reply:
            return comment

    for comment, score in scored:
        if score >= 70:
            return comment

    op_confirmed = [c for c in candidates if c.is_op_reply]
    if op_confirmed:
        return max(op_confirmed, key=lambda c: c.score)

    return None


_CHARS_PER_TOKEN = 4   # conservative estimate; avoids importing the tokenizer here

def _format_input(
    post: Post,
    comment: Comment,
    op_reply: Optional[Comment],
    max_length: int = 384,
) -> str:
    """
    Format a (post, comment, op_reply) triple as a single string for the model.

    Layout:
        {title}
        {body}          ← truncated if needed to protect comment + op_reply
        ---
        {comment}
        [OP]
        {op_reply}      ← omitted when absent

    Pre-truncating the post body here ensures HuggingFace's tokenizer never has
    to truncate from the right and accidentally drops the comment or OP reply,
    which carry the strongest classification signal.
    """
    comment_text = comment.body
    op_text = op_reply.body if op_reply else ""

    # Characters reserved for the fixed parts of the template
    fixed_chars = len("---\n") + len("[OP]\n") + len("\n\n\n")
    used = len(comment_text) + len(op_text) + fixed_chars
    body_budget = max((max_length * _CHARS_PER_TOKEN) - used - len(post.title), 0)

    body = post.body[:body_budget] if len(post.body) > body_budget else post.body
    post_text = f"{post.title}\n{body}".strip()

    parts = [post_text, "---", comment_text]
    if op_reply:
        parts += ["[OP]", op_text]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Training data
# ---------------------------------------------------------------------------

@dataclass
class TrainingExample:
    text: str
    label: int       # 1 = answer comment, 0 = not the answer
    post_id: str
    comment_id: str


class BootstrapDataBuilder:
    """
    Builds labeled training examples from flaired posts.

    Only flaired posts are used — unflaired posts may be secretly solved and
    would add label noise if treated as hard negatives.
    """

    NEGATIVE_RATIO = 3   # negatives per positive after downsampling

    def build(self, posts: list[Post]) -> list[TrainingExample]:
        examples: list[TrainingExample] = []
        for post in posts:
            if not post.flair:
                continue
            examples.extend(self._from_post(post))
        return examples

    def _from_post(self, post: Post) -> list[TrainingExample]:
        answer = find_answer_comment(post, post.flair)
        if answer is None:
            return []

        positives: list[TrainingExample] = []
        negatives: list[TrainingExample] = []

        for comment in post.comments:
            if comment.author in ("[deleted]", "AutoModerator", post.author, ""):
                continue
            if comment.body in ("[deleted]", "[removed]", ""):
                continue

            op_reply = get_op_reply(post, comment)
            text = _format_input(post, comment, op_reply, max_length=SolvedClassifier.MAX_LENGTH)
            example = TrainingExample(
                text=text,
                label=1 if comment.id == answer.id else 0,
                post_id=post.id,
                comment_id=comment.id,
            )
            (positives if example.label == 1 else negatives).append(example)

        if not positives:
            return []

        # Downsample negatives to keep class imbalance manageable
        random.shuffle(negatives)
        negatives = negatives[: len(positives) * self.NEGATIVE_RATIO]
        return positives + negatives


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

class SolvedClassifier:
    """
    DistilBERT-based binary classifier.

    For each (post, comment) pair the model scores "is this the answer comment?".
    At inference, all comments in a post are scored; the highest scorer is
    returned as the answer if its confidence exceeds the caller's threshold.
    """

    MAX_LENGTH = 384

    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        self._tokenizer = None
        self._model = None

    def load(self) -> "SolvedClassifier":
        from transformers import DistilBertForSequenceClassification, DistilBertTokenizerFast

        self._tokenizer = DistilBertTokenizerFast.from_pretrained(self.model_path)
        self._model = DistilBertForSequenceClassification.from_pretrained(self.model_path)
        self._model.eval()
        return self

    # ------------------------------------------------------------------

    def predict(self, post: Post) -> tuple[bool, Optional[Comment], float]:
        """
        Returns (is_solved, answer_comment, confidence).
        answer_comment is None when is_solved is False.
        """
        import torch

        mark_op_replies(post)
        pairs = self._build_candidate_pairs(post)
        if not pairs:
            return False, None, 0.0

        texts = [text for _, text in pairs]
        inputs = self._tokenizer(
            texts,
            truncation=True,
            max_length=self.MAX_LENGTH,
            padding=True,
            return_tensors="pt",
        )

        with torch.no_grad():
            logits = self._model(**inputs).logits
            probs = torch.softmax(logits, dim=-1)[:, 1]

        best_idx = int(probs.argmax())
        confidence = float(probs[best_idx])
        answer = pairs[best_idx][0]

        return confidence > 0.5, answer, confidence

    def predict_batch(self, posts: list[Post]) -> list[tuple[bool, Optional[Comment], float]]:
        return [self.predict(p) for p in posts]

    def to_confirmed_pair(
        self, post: Post, answer: Comment, confidence: float
    ) -> ConfirmedPair:
        return ConfirmedPair(
            post_id=post.id,
            subreddit=post.subreddit,
            description=f"{post.title}\n\n{post.body}".strip(),
            answer=answer.body,
            answer_comment_id=answer.id,
            confidence=confidence,
            flair=post.flair,
            created_utc=post.created_utc,
        )

    # ------------------------------------------------------------------

    def _build_candidate_pairs(
        self, post: Post
    ) -> list[tuple[Comment, str]]:
        pairs = []
        for comment in post.comments:
            if comment.author in ("[deleted]", "AutoModerator", post.author, ""):
                continue
            if comment.body in ("[deleted]", "[removed]", ""):
                continue
            op_reply = get_op_reply(post, comment)
            pairs.append((comment, _format_input(post, comment, op_reply, max_length=self.MAX_LENGTH)))
        return pairs

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    @classmethod
    def train(
        cls,
        examples: list[TrainingExample],
        output_path: str,
        base_model: str = "distilbert-base-uncased",
        num_epochs: int = 3,
        batch_size: int = 8,
        gradient_accumulation_steps: int = 2,
    ) -> "SolvedClassifier":
        # Default batch_size=8 + accumulation=2 → effective batch of 16 while
        # keeping peak VRAM under ~5GB, comfortable for an 8GB card.
        import torch
        from datasets import Dataset
        from transformers import (
            DistilBertForSequenceClassification,
            DistilBertTokenizerFast,
            Trainer,
            TrainingArguments,
        )

        tokenizer = DistilBertTokenizerFast.from_pretrained(base_model)
        model = DistilBertForSequenceClassification.from_pretrained(
            base_model, num_labels=2
        )

        shuffled = list(examples)
        random.shuffle(shuffled)

        ds = Dataset.from_dict({
            "text": [e.text for e in shuffled],
            "label": [e.label for e in shuffled],
        })

        def tokenize(batch):
            return tokenizer(
                batch["text"],
                truncation=True,
                max_length=cls.MAX_LENGTH,
                padding="max_length",
            )

        ds = ds.map(tokenize, batched=True, remove_columns=["text"])
        split = ds.train_test_split(test_size=0.1, seed=42)

        training_args = TrainingArguments(
            output_dir=output_path,
            num_train_epochs=num_epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            eval_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            logging_steps=50,
            fp16=torch.cuda.is_available(),
            report_to="none",
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=split["train"],
            eval_dataset=split["test"],
        )
        trainer.train()

        model.save_pretrained(output_path)
        tokenizer.save_pretrained(output_path)

        return cls(output_path).load()

    def push_to_hub(self, repo_id: str) -> None:
        assert self._model and self._tokenizer, "Call load() first"
        self._model.push_to_hub(repo_id)
        self._tokenizer.push_to_hub(repo_id)
