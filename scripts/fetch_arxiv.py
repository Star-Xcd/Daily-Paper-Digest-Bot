import time
import yaml
import feedparser
import requests

from datetime import datetime, timedelta, timezone
from dateutil import parser as dtparser

ARXIV_API = "http://export.arxiv.org/api/query"


def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_query(queries):
    return " OR ".join(f"({q})" for q in queries)


def fetch_one_query(search_query, start=0, max_results=100):
    params = {
        "search_query": search_query,
        "start": start,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    r = requests.get(ARXIV_API, params=params, timeout=30)
    r.raise_for_status()
    return feedparser.parse(r.text)


def normalize_entry(entry):
    authors = [a.name for a in entry.get("authors", [])]
    links = entry.get("links", [])
    pdf_url = None
    for link in links:
        if link.get("type") == "application/pdf":
            pdf_url = link.get("href")
            break

    return {
        "id": entry.id.split("/abs/")[-1],
        "title": " ".join(entry.title.split()),
        "summary": " ".join(entry.summary.split()),
        "authors": authors,
        "published": entry.published,
        "updated": entry.updated,
        "url": entry.link,
        "pdf_url": pdf_url,
        "tags": [t.term for t in entry.get("tags", [])],
        "source": "arxiv",
    }


def fetch_candidates(config_path):
    cfg = load_config(config_path)
    queries = list(cfg["source_queries"]["arxiv_queries"])
    author_cfg = cfg.get("author_spotlight", {})
    authors = author_cfg.get("authors", [])
    if authors:
        queries.append(build_query([f'au:"{author}"' for author in authors]))
    now = datetime.now(timezone.utc)
    lookback_days = cfg["source_queries"].get(
        "lookback_days",
        author_cfg.get("lookback_days", 90),
    )
    cutoff = now - timedelta(days=lookback_days)

    all_items = {}
    for q in queries:
        feed = fetch_one_query(q, start=0, max_results=80)
        for entry in feed.entries:
            item = normalize_entry(entry)
            published_dt = dtparser.parse(item["published"])
            if published_dt < cutoff:
                continue
            all_items[item["id"]] = item
        time.sleep(3.5)  # Keep a polite delay between arXiv API requests.

    return list(all_items.values())
