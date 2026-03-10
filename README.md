# Daily Paper Digest Bot

This repository runs a GitHub Actions workflow that fetches recent arXiv papers, selects three papers per day, generates an English research brief with Gemini, and sends the digest by email.

## What It Does

Each daily run executes this pipeline:

1. Fetch recent arXiv candidates from robotics- and ML-related queries.
2. Rank papers into three buckets:
   - most relevant to your recent work
   - interest-based topic recommendation
   - a representative paper from a configured author shortlist in the last three months
3. Generate an English digest with Gemini.
4. Send the digest through SMTP.
5. Persist sent paper IDs to avoid repeats across future runs.

If Gemini summarization fails, the pipeline automatically falls back to a plain English template email built directly from the selected paper metadata.

## Repository Layout

```text
.
├── .github/workflows/daily_papers.yml
├── config/topics.yaml
├── data/history.json
├── requirements.txt
└── scripts
    ├── fetch_arxiv.py
    ├── main.py
    ├── rank_papers.py
    ├── send_email.py
    └── summarize_with_llm.py
```

## Requirements

- Python 3.11
- A Gemini API key (Gemini has free quota every month. You can use your own API keys from other sources, but you need to modify [`summarize_with_llm.py`].)
- An SMTP account that supports `STARTTLS`
- A GitHub repository with Actions enabled

## GitHub Actions Deployment

The workflow file is [`.github/workflows/daily_papers.yml`](.github/workflows/daily_papers.yml). Currently it is scheduled to run every day at `00:30 UTC`, which is `08:30` in Beijing/Taipei.

To deploy:

1. Push this repository to GitHub.
2. In the repository, open `Settings -> Secrets and variables -> Actions`.
3. Add these repository secrets:
   - `GEMINI_API_KEY`
   - `SMTP_HOST`
   - `SMTP_PORT`
   - `SMTP_USER`
   - `SMTP_PASS`
   - `EMAIL_TO`
4. Optionally add `GEMINI_MODEL` if you want to override the default model. If unset, the code uses `gemini-2.5-flash`.
5. In `Settings -> Actions -> General`, make sure GitHub Actions is enabled.
6. In the workflow permissions section, allow read and write access to repository contents, because the workflow commits `data/history.json` and `data/latest_digest.json`.
7. Manually trigger the workflow once from the `Actions` tab with `workflow_dispatch` to verify the setup.

## SMTP Notes

The email sender uses SMTP with `STARTTLS`. Typical values look like:

- `SMTP_HOST`: `smtp.gmail.com`. (If you are using Gmail)
- `SMTP_PORT`: `587`

If you use Gmail, you will usually need an app password rather than your normal account password.

## Local Setup

Create and activate a Conda environment, then install dependencies:

```bash
conda create -n paper-digest python=3.11 -y
conda activate paper-digest
pip install -r requirements.txt
```

Set the required environment variables:

```bash
export GEMINI_API_KEY="..."
export GEMINI_MODEL="gemini-2.5-flash"
export SMTP_HOST="smtp.example.com"
export SMTP_PORT="587"
export SMTP_USER="bot@example.com"
export SMTP_PASS="..."
export EMAIL_TO="you@example.com"
```

Run the pipeline:

```bash
python scripts/main.py
```

## Configuration

Edit [`config/topics.yaml`](config/topics.yaml) to tune:

- positive keywords for recent-work matching
- negative keywords to suppress irrelevant domains
- topic interests
- spotlight authors and their lookback window
- arXiv source queries
- the Gemini model through the `GEMINI_MODEL` environment variable if needed

## Outputs

Each successful run updates:

- [`data/history.json`](data/history.json): sent paper IDs used for deduplication
- [`data/latest_digest.json`](data/latest_digest.json): the three selected papers from the latest run

## Operational Notes

- The workflow depends on external services: arXiv, Gemini, and your SMTP provider.
- GitHub Actions scheduled workflows are not guaranteed to start at the exact minute.
- If no eligible papers are selected, the script exits without sending email.
- The repository currently stores deduplication state in Git. That is simple and effective for a single daily workflow, but it is not designed for high-frequency concurrent runs.
