import yaml
from dateutil import parser as dtparser
from datetime import datetime, timedelta, timezone


def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def text_of(paper):
    return f"{paper['title']} {paper['summary']}".lower()


def count_keyword_hits(text, keywords):
    return sum(1 for kw in keywords if kw.lower() in text)


def recency_score(paper):
    now = datetime.now(timezone.utc)
    published = dtparser.parse(paper["published"])
    age_days = max((now - published).days, 0)
    return max(0.0, 1.0 - age_days / 60.0)


def recent_work_score(paper, cfg):
    text = text_of(paper)
    pos = count_keyword_hits(text, cfg["recent_work"]["keywords"])
    neg = count_keyword_hits(text, cfg["recent_work"]["negative_keywords"])
    return 2.0 * pos - 1.5 * neg + recency_score(paper)


def interest_score(paper, cfg):
    text = text_of(paper)
    return count_keyword_hits(text, cfg["interest_topics"]) + 0.8 * recency_score(paper)


def has_spotlight_author(paper, authors):
    author_names = {name.lower() for name in paper.get("authors", [])}
    return any(author.lower() in author_names for author in authors)


def author_spotlight_score(paper, cfg):
    spotlight_cfg = cfg.get("author_spotlight", {})
    authors = spotlight_cfg.get("authors", [])
    if not has_spotlight_author(paper, authors):
        return float("-inf")

    lookback_days = spotlight_cfg.get("lookback_days", 90)
    published = dtparser.parse(paper["published"])
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    if published < cutoff:
        return float("-inf")

    text = text_of(paper)
    return (
        1.0 * recent_work_score(paper, cfg)
        + 1.6 * interest_score(paper, cfg)
        + 0.6 * recency_score(paper)
        + 0.2 * count_keyword_hits(text, ["robot", "manipulation", "policy", "dexterous"])
    )


def select_best(candidates, used_ids, score_fn):
    pool = [p for p in candidates if p["id"] not in used_ids]
    if not pool:
        return None
    pool.sort(key=score_fn, reverse=True)
    return pool[0]


def select_daily_picks(candidates, config_path, sent_ids):
    cfg = load_config(config_path)
    used_ids = set(sent_ids)

    recent_pick = select_best(candidates, used_ids, lambda p: recent_work_score(p, cfg))
    if recent_pick:
        recent_pick["bucket"] = "Most relevant to your recent work"
        used_ids.add(recent_pick["id"])

    interest_pick = select_best(candidates, used_ids, lambda p: interest_score(p, cfg))
    if interest_pick:
        interest_pick["bucket"] = "Interest-based topic recommendation"
        used_ids.add(interest_pick["id"])

    author_pick = select_best(candidates, used_ids, lambda p: author_spotlight_score(p, cfg))
    if author_pick and author_spotlight_score(author_pick, cfg) != float("-inf"):
        author_pick["bucket"] = "Representative paper from your selected authors in the last three months"
        used_ids.add(author_pick["id"])

    result = [p for p in [recent_pick, interest_pick, author_pick] if p is not None]
    return result
