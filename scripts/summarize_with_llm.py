import os
from html import escape
from google import genai

_CLIENT = None


def get_client():
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _CLIENT


def build_prompt(selected):
    blocks = []
    for i, p in enumerate(selected, 1):
        blocks.append(
            f"""[{i}] Bucket: {p['bucket']}
Title: {p['title']}
Authors: {", ".join(p['authors'][:8])}
Published: {p['published']}
Abstract: {p['summary']}
Link: {p['url']}
"""
        )

    return f"""
Generate an English daily paper digest email based on the three papers below.

Requirements:
1. Write everything in English.
2. Start with a concise, professional title on the first line.
3. Follow with a 3-5 sentence overview for a robotics researcher.
4. For each paper, include:
   - Title
   - Why it was selected, tied to its bucket
   - A 2-3 sentence method summary
   - A 1-2 sentence note on why it is worth reading
   - The original link
5. Use a crisp research-brief tone, not marketing language.
6. When relevant, connect the paper to manipulation, dexterous manipulation, vision-language-action, or robot learning.
7. Format the output as clean plain text with short paragraphs and section headers.

Paper information:
{chr(10).join(blocks)}
"""


def call_llm():
    raise NotImplementedError


def summarize_digest_text(selected):
    prompt = build_prompt(selected)
    try:
        resp = get_client().models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=prompt,
        )
    except Exception as exc:
        raise RuntimeError(f"Gemini generation failed: {exc}") from exc
    return resp.text


def summarize_digest_fallback_text(selected):
    overview = (
        "Daily Robotics Paper Digest\n\n"
    #     "This digest was generated with the fallback template because the LLM summary step "
    #     "was unavailable. The three papers below were still selected by the ranking pipeline "
    #     "and are grouped by relevance, topical interest, and broader robotics impact.\n"
    )

    sections = [overview]
    for i, paper in enumerate(selected, 1):
        authors = ", ".join(paper["authors"][:8]) if paper.get("authors") else "Unknown authors"
        sections.append(
            "\n".join(
                [
                    f"Paper {i}: {paper['title']}",
                    f"Bucket: {paper['bucket']}",
                    f"Authors: {authors}",
                    f"Published: {paper['published']}",
                    f"Why it was selected: This paper ranked highest in the '{paper['bucket']}' bucket.",
                    f"Abstract: {paper['summary']}",
                    f"Link: {paper['url']}",
                ]
            )
        )

    return "\n\n".join(sections)


def summarize_digest_html(text):
    html = "<html><body style='font-family:Arial,sans-serif;line-height:1.6;'>"
    html += "".join(f"<p>{escape(line)}</p>" for line in text.split("\n") if line.strip())
    html += "</body></html>"
    return html
