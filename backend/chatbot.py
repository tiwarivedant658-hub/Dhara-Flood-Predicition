"""
chatbot.py
----------
A small, dependency-free, rule-based chatbot that answers questions about
flash flood prevention, preparedness and how the risk map works, using
data/knowledge_base.json.

Why rule-based and not an LLM call: it needs zero API keys/cost, works
completely offline (handy in a hilly-region field demo with poor network),
and answers are 100% predictable for a judge Q&A. If your team wants to
upgrade it to a generative model later, docs/API.md shows exactly where to
swap in an LLM call (e.g. the Anthropic API) without touching the frontend.

Matching approach: for each knowledge-base entry we count how many of its
keywords appear as substrings of the user's (lower-cased) message, and
return the entry with the highest hit-count. Ties go to the first match in
file order. Below MIN_SCORE we return the default fallback answer.
"""

import json
from pathlib import Path

MIN_SCORE = 1
_KB_PATH = Path(__file__).resolve().parent.parent / "data" / "knowledge_base.json"

with open(_KB_PATH, "r", encoding="utf-8") as f:
    _KB = json.load(f)


def get_greeting() -> str:
    return _KB["greeting"][0]


def answer(message: str) -> dict:
    """
    Returns {"reply": str, "matched_id": str | None}
    """
    text = (message or "").lower().strip()
    if not text:
        return {"reply": get_greeting(), "matched_id": None}

    best_entry = None
    best_score = 0

    for entry in _KB["entries"]:
        score = sum(1 for kw in entry["keywords"] if kw in text)
        if score > best_score:
            best_score = score
            best_entry = entry

    if best_entry and best_score >= MIN_SCORE:
        return {"reply": best_entry["answer"], "matched_id": best_entry["id"]}

    return {"reply": _KB["default"], "matched_id": None}
