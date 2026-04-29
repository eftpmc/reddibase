# Reddibase

An open-source platform for training and hosting identification models built from Reddit archives. Subreddits like r/tipofmyjoystick — where people post vague descriptions and the community identifies the answer — are scraped, cleaned, and turned into searchable datasets and retrieval models.

## How it works

Each model covers one subreddit and ships two things:

1. **reddibase-classifier** — reads a post's comment thread and determines whether it reached an identified answer and which comment contains it
2. **Identification model** — takes a vague description and returns ranked matches from the confirmed dataset

Data comes from [Arctic Shift](https://arctic-shift.photon-reddit.com), a full Reddit archive with no 1000-post limit. Flair is used only as a training signal for the classifier — it is never used at inference.

## Searching

Once a model is trained and registered, search is available at:

```
GET /models/{model_id}/search?q=your+description&top_k=10
```

Or through the web UI — pick a model from the registry, type a vague description, get ranked matches with similarity scores.

## Current models

| Model | Subreddit | Pairs |
|---|---|---|
| tipofmyjoystick | r/tipofmyjoystick | — |

---

## Contributing a new model

### What you need

- A Google account (for Colab and Google Drive)
- A [Hugging Face](https://huggingface.co) account with a write-access token
- A subreddit that has a "vague description → confirmed answer" pattern

### Step 1 — Open the notebook

Open `notebooks/train.ipynb` in Google Colab. Enable the T4 GPU: **Runtime → Change runtime type → T4 GPU**.

The notebook has 8 sections and handles everything automatically — scraping, training, pushing to Hugging Face, and generating the config for your PR.

### Step 2 — Fill in three fields

In the Configuration cell:

- `subreddit` — subreddit name without r/ (e.g. `tipofmyjoystick`)
- `hf_repo` — where to push the model (e.g. `your-username/tipofmyjoystick-identification`)
- `hf_token` — your Hugging Face write token

Set `flair_strategy` if your subreddit uses specific flair values for solved posts rather than the game/answer name as the flair.

### Step 3 — Run all cells

**Runtime → Run all**, then leave it overnight. Here is what each section does and roughly how long it takes:

**Section 2.5 — API verification (instant)**
Hits the Arctic Shift API for 3 posts and prints the raw field names. Check that `link_flair_text`, `created_utc`, `author`, and `body` are all present before committing to a long scrape. If something looks wrong, stop here and open an issue.

**Section 3 — Scraping (2–8 hours)**
Pulls every post and full comment thread from the Arctic Shift archive. Checkpoints to your Google Drive every 1000 posts. If your session disconnects, re-run this cell and it resumes automatically from where it stopped.

```
Starting fresh scrape
  Checkpoint: 1,000 total posts
  Checkpoint: 2,000 total posts
  ...
Done. 347,821 posts, 201,455 flaired (57.9%)
```

**Section 4 — reddibase-classifier training (2–4 hours)**
Fine-tunes DistilBERT on posts where a flair exists. The flair is the answer (e.g. the game name), so training examples are extracted by matching the flair text against comments. You will see the standard HuggingFace Trainer output:

```
{'loss': 0.693, 'epoch': 1.0}
{'eval_loss': 0.421, 'epoch': 1.0}
{'loss': 0.312, 'epoch': 2.0}
{'eval_loss': 0.289, 'epoch': 2.0}
...
```

**Section 5 — Build dataset (30–60 minutes)**
Runs reddibase-classifier over all posts, including unflaired ones, to recover identified posts that OP never flaired. Saves pairs above the confidence threshold to `confirmed_pairs.jsonl` on your Drive.

```
Classifying: 100%|████████| 347,821/347,821
Confirmed: 198,304 / 347,821
```

**Section 6 — Identification model (30–60 minutes)**
Fine-tunes a Sentence Transformer on the confirmed pairs and builds the static FAISS index.

```
Pairs: 198,304  unique answers: 94,712
Training examples: 287,441
...
Encoding 198,304 descriptions...
Index: 198,304 vectors, dim=384 → .../identification_model/
```

**Section 7 — Push to Hugging Face Hub (5–10 minutes)**
Uploads the encoder weights, `index.faiss`, and `pairs.jsonl` to your HF repo.

```
Uploaded index.faiss
Uploaded pairs.jsonl
Model live at https://huggingface.co/your-username/tipofmyjoystick-identification
```

**Section 8 — Generate config**
Prints a ready-to-paste `config.yaml`. Copy it.

### Step 4 — Open a pull request

1. Fork this repo
2. Create `models/{subreddit}/config.yaml` with the output from Section 8 (fill in `display_name` and `description`)
3. Open a PR — your model will appear in the registry once merged

---

## Running locally

```bash
git clone https://github.com/YOUR_USERNAME/reddibase
cd reddibase
pip install -r requirements.txt
uvicorn api.main:app --reload
```

The search, registry, and dataset routes work from local configs plus trained artifacts. Model metadata lives in `models/{model_id}/config.yaml`; search and dataset browsing load `index.faiss` and `pairs.jsonl` from the model artifact cache.

To train a model locally instead of on Colab:

```bash
# Scrape (runs overnight, restartable)
python -m scripts.train_classifier tipofmyjoystick --cache posts.pkl

# Run reddibase-classifier over all posts → confirmed pairs
python -m scripts.build_dataset tipofmyjoystick --cache posts.pkl

# Fine-tune encoder + build FAISS index
python -m scripts.train_embedder tipofmyjoystick
```

Default settings target an 8 GB VRAM GPU (batch size 8, gradient accumulation 2, max sequence length 384). Adjust in `framework/classifier.py` if your card has more headroom.

---

## Repo structure

```
framework/
  scraper.py       Arctic Shift API client — streams all posts and comments
  classifier.py    reddibase-classifier — bootstrap training + inference
  embedder.py      Identification model — fine-tune encoder + FAISS index
  schema.py        Shared dataclasses (Post, Comment, ConfirmedPair)

models/
  tipofmyjoystick/
    config.yaml    Subreddit-specific configuration

scripts/
  train_classifier.py   CLI for reddibase-classifier training
  build_dataset.py      CLI for running reddibase-classifier → confirmed pairs
  train_embedder.py     CLI for encoder fine-tuning + index building

notebooks/
  train.ipynb      Colab notebook — full pipeline for contributors

api/
  main.py          FastAPI app
  routes/
    search.py      Search endpoint (functional)
    models.py      Model registry endpoint (stub)
    dataset.py     Dataset browser + download (stub)

web/               Next.js frontend (coming soon)
```
