"""
Resolved-thread classifier.

The classifier learns to identify which message in a human discussion contains
the resolved answer. Weak labels come from source adapters, such as Reddit
flairs, accepted-answer markers, or other source-specific resolution signals.
"""

import random
from dataclasses import dataclass
from typing import Optional

from rapidfuzz import fuzz

from framework.schema import ConfirmedPair, Message, Thread

DELETED_AUTHORS = {"[deleted]", "AutoModerator", ""}
DELETED_BODIES = {"[deleted]", "[removed]", ""}
_CHARS_PER_TOKEN = 4


def mark_author_replies(thread: Thread) -> None:
    """
    Annotate messages when the original thread author directly replied to them.

    Reddit parent IDs use t1_{comment_id}; other adapters can prefill
    metadata["is_author_reply"] if their parent IDs follow a different shape.
    """
    author = thread.author_id
    if author in DELETED_AUTHORS:
        return

    reply_targets = {
        m.parent_id
        for m in thread.messages
        if m.author_id == author and m.parent_id and m.parent_id.startswith("t1_")
    }

    for message in thread.messages:
        message.metadata["is_author_reply"] = f"t1_{message.source_id}" in reply_targets


def get_author_reply(thread: Thread, message: Message) -> Optional[Message]:
    """Return the thread author's direct reply to a message, if one exists."""
    for candidate in thread.messages:
        if (
            candidate.author_id == thread.author_id
            and candidate.parent_id == f"t1_{message.source_id}"
        ):
            return candidate
    return None


def is_answer_candidate(thread: Thread, message: Message) -> bool:
    return (
        message.author_id not in DELETED_AUTHORS
        and message.author_id != thread.author_id
        and message.body not in DELETED_BODIES
    )


def find_answer_message(thread: Thread, weak_answer: str) -> Optional[Message]:
    """
    Best-effort answer-message lookup for weakly labeled solved threads.

    Priority:
    1. Message fuzzy-matches weak answer and thread author replied to it.
    2. Message fuzzy-matches weak answer.
    3. Highest-scored message the thread author replied to.
    """
    mark_author_replies(thread)

    candidates = [m for m in thread.messages if is_answer_candidate(thread, m)]
    if not candidates:
        return None

    scored = sorted(
        [(m, fuzz.partial_ratio(weak_answer.lower(), m.body.lower())) for m in candidates],
        key=lambda x: (x[1], x[0].score),
        reverse=True,
    )

    for message, score in scored:
        if score >= 60 and message.metadata.get("is_author_reply"):
            return message

    for message, score in scored:
        if score >= 70:
            return message

    author_confirmed = [m for m in candidates if m.metadata.get("is_author_reply")]
    if author_confirmed:
        return max(author_confirmed, key=lambda m: m.score)

    return None


def format_classifier_input(
    thread: Thread,
    message: Message,
    author_reply: Optional[Message],
    max_length: int = 384,
) -> str:
    message_text = message.body
    reply_text = author_reply.body if author_reply else ""

    fixed_chars = len("---\n") + len("[AUTHOR]\n") + len("\n\n\n")
    used = len(message_text) + len(reply_text) + fixed_chars
    body_budget = max((max_length * _CHARS_PER_TOKEN) - used - len(thread.title), 0)

    body = thread.body[:body_budget] if len(thread.body) > body_budget else thread.body
    thread_text = f"{thread.title}\n{body}".strip()

    parts = [thread_text, "---", message_text]
    if author_reply:
        parts += ["[AUTHOR]", reply_text]
    return "\n".join(parts)


@dataclass
class TrainingExample:
    text: str
    label: int
    thread_id: str
    message_id: str


class BootstrapDataBuilder:
    """
    Builds labeled examples from weakly answered threads.

    Threads without weak_answer are skipped because they may still be secretly
    solved and would add noisy hard negatives.
    """

    NEGATIVE_RATIO = 3

    def build(self, threads: list[Thread]) -> list[TrainingExample]:
        examples: list[TrainingExample] = []
        for thread in threads:
            if thread.weak_answer:
                examples.extend(self._from_thread(thread))
        return examples

    def _from_thread(self, thread: Thread) -> list[TrainingExample]:
        if not thread.weak_answer:
            return []

        answer = find_answer_message(thread, thread.weak_answer)
        if answer is None:
            return []

        positives: list[TrainingExample] = []
        negatives: list[TrainingExample] = []

        for message in thread.messages:
            if not is_answer_candidate(thread, message):
                continue

            author_reply = get_author_reply(thread, message)
            text = format_classifier_input(
                thread,
                message,
                author_reply,
                max_length=ResolvedThreadClassifier.MAX_LENGTH,
            )
            example = TrainingExample(
                text=text,
                label=1 if message.id == answer.id else 0,
                thread_id=thread.id,
                message_id=message.id,
            )
            (positives if example.label == 1 else negatives).append(example)

        if not positives:
            return []

        random.shuffle(negatives)
        negatives = negatives[: len(positives) * self.NEGATIVE_RATIO]
        return positives + negatives


class ResolvedThreadClassifier:
    """
    DistilBERT-based binary classifier.

    For each (thread, message) pair, the model scores whether that message is
    the answer. At inference, all candidate messages are scored and the highest
    scorer is returned with confidence.
    """

    MAX_LENGTH = 384

    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        self._tokenizer = None
        self._model = None

    def load(self) -> "ResolvedThreadClassifier":
        from transformers import DistilBertForSequenceClassification, DistilBertTokenizerFast

        self._tokenizer = DistilBertTokenizerFast.from_pretrained(self.model_path)
        self._model = DistilBertForSequenceClassification.from_pretrained(self.model_path)
        self._model.eval()
        return self

    def predict(self, thread: Thread) -> tuple[bool, Optional[Message], float]:
        import torch

        mark_author_replies(thread)
        pairs = self._build_candidate_pairs(thread)
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

    def predict_batch(self, threads: list[Thread]) -> list[tuple[bool, Optional[Message], float]]:
        return [self.predict(thread) for thread in threads]

    def to_confirmed_pair(
        self, thread: Thread, answer: Message, confidence: float
    ) -> ConfirmedPair:
        return ConfirmedPair(
            thread_id=thread.id,
            source=thread.source,
            source_id=thread.source_id,
            community=thread.community,
            description=f"{thread.title}\n\n{thread.body}".strip(),
            answer=answer.body,
            answer_message_id=answer.id,
            confidence=confidence,
            weak_answer=thread.weak_answer,
            created_utc=thread.created_utc,
            post_id=thread.source_id,
            subreddit=thread.community,
            answer_comment_id=answer.source_id,
            flair=thread.weak_answer,
        )

    def _build_candidate_pairs(self, thread: Thread) -> list[tuple[Message, str]]:
        pairs = []
        for message in thread.messages:
            if not is_answer_candidate(thread, message):
                continue
            author_reply = get_author_reply(thread, message)
            pairs.append((
                message,
                format_classifier_input(thread, message, author_reply, self.MAX_LENGTH),
            ))
        return pairs

    @classmethod
    def train(
        cls,
        examples: list[TrainingExample],
        output_path: str,
        base_model: str = "distilbert-base-uncased",
        num_epochs: int = 3,
        batch_size: int = 8,
        gradient_accumulation_steps: int = 2,
    ) -> "ResolvedThreadClassifier":
        import torch
        from datasets import Dataset
        from transformers import (
            DistilBertForSequenceClassification,
            DistilBertTokenizerFast,
            Trainer,
            TrainingArguments,
        )

        tokenizer = DistilBertTokenizerFast.from_pretrained(base_model)
        model = DistilBertForSequenceClassification.from_pretrained(base_model, num_labels=2)

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
