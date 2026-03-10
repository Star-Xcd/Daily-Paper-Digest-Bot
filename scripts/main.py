import json
from pathlib import Path
from json import JSONDecodeError

from fetch_arxiv import fetch_candidates
from rank_papers import select_daily_picks
from summarize_with_llm import (
    summarize_digest_fallback_text,
    summarize_digest_html,
    summarize_digest_text,
)
from send_email import send_email

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "topics.yaml"
HISTORY_PATH = ROOT / "data" / "history.json"
LATEST_PATH = ROOT / "data" / "latest_digest.json"


def load_history():
    if HISTORY_PATH.exists():
        try:
            history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        except JSONDecodeError:
            return {"sent_ids": []}
        if isinstance(history, dict) and isinstance(history.get("sent_ids"), list):
            return history
    return {"sent_ids": []}


def save_history(history):
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def main():
    history = load_history()
    candidates = fetch_candidates(CONFIG_PATH)
    print("Candidates fetched.")
    selected = select_daily_picks(candidates, CONFIG_PATH, history["sent_ids"])

    if not selected:
        print("No papers selected today.")
        return
    
    print("Papers selected.")

    try:
        text_body = summarize_digest_text(selected)
        print("LLM summary generated.")
    except Exception as exc:
        print(f"LLM summary failed. Falling back to template email. Error: {exc}")
        text_body = summarize_digest_fallback_text(selected)

    html_body = summarize_digest_html(text_body)

    print("Ready to send email.")

    send_email(
        subject="Daily Robotics Paper Digest",
        html_body=html_body,
        text_body=text_body,
    )

    history["sent_ids"].extend([p["id"] for p in selected])
    history["sent_ids"] = history["sent_ids"][-5000:]
    save_history(history)

    LATEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    LATEST_PATH.write_text(
        json.dumps(selected, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


if __name__ == "__main__":
    main()
