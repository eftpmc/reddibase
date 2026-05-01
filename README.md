# Reddibase

Reddibase turns human-solved discussion threads into answer-extraction datasets
and identification models.

The core artifact is a source-neutral `Thread`: a vague request or problem,
its messages, and optional weak answer signals from the source. Reddit is the
first adapter, but the classifier and identifier work from `threads.jsonl`, not
Reddit-specific post objects.

## How It Works

Each model ships two pieces:

1. **Resolved-thread classifier**: reads a discussion thread and identifies the
   message that contains the resolved answer.
2. **Identification model**: embeds vague descriptions and retrieves ranked
   matches from confirmed `(description -> answer)` pairs.

The pipeline is:

```text
source adapter -> threads.jsonl
threads.jsonl -> resolved-thread classifier
threads.jsonl + classifier -> confirmed_pairs.jsonl
confirmed_pairs.jsonl -> SentenceTransformer + FAISS index
```

## Local Pipeline

Install dependencies:

```bash
pip install -r requirements.txt
```

Scrape Reddit/Arctic Shift directly into source-neutral threads:

```bash
python -m scripts.scrape_threads tipofmyjoystick \
  --output data/converted/tipofmyjoystick/threads.jsonl
```

Audit the thread artifact before training:

```bash
python -m scripts.audit_threads tipofmyjoystick \
  --threads data/converted/tipofmyjoystick/threads.jsonl
```

Train the resolved-thread classifier:

```bash
python -m scripts.train_classifier tipofmyjoystick \
  --threads data/converted/tipofmyjoystick/threads.jsonl
```

Extract confirmed answer pairs:

```bash
python -m scripts.build_dataset tipofmyjoystick \
  --threads data/converted/tipofmyjoystick/threads.jsonl
```

Train the identification model and FAISS index:

```bash
python -m scripts.train_embedder tipofmyjoystick
```

The same flow is available as small local workflow notebooks:

```text
notebooks/scrape_threads.ipynb
notebooks/train_classifier_extract_pairs.ipynb
notebooks/train_identifier.ipynb
```

## Searching

Once a model is trained and registered:

```text
GET /models/{model_id}/search?q=your+description&top_k=10
```

Run the API locally:

```bash
uvicorn api.main:app --reload
```

Run the web UI from `web/`:

```bash
npm install
npm run dev
```

## Current Models

| Model | Source | Community | Pairs |
|---|---|---|---|
| tipofmyjoystick | reddit | r/tipofmyjoystick | - |

## Repo Structure

```text
framework/
  schema.py      Source-neutral Thread, Message, ConfirmedPair dataclasses
  threads.py     JSONL read/write helpers for Thread artifacts
  scraper.py     Reddit/Arctic Shift adapter that streams Thread objects
  classifier.py  Resolved-thread classifier training + inference
  embedder.py    Identification model + FAISS index

scripts/
  scrape_threads.py    Scrape source-neutral threads.jsonl
  audit_threads.py     Audit weak-answer and message coverage before training
  train_classifier.py  Train resolved-thread classifier
  build_dataset.py     Extract confirmed pairs from threads
  train_embedder.py    Train identifier + build FAISS

models/
  tipofmyjoystick/
    config.yaml

api/
web/
```
