import json
import re
import sys
from urllib.parse import urlparse


def classify_input(text: str):
    text = text.strip()
    if text.startswith(("http://", "https://")):
        if text.lower().endswith(".pdf"):
            return "pdf_url"
        return "url"
    if re.match(r"^10\.\d{4,9}/\S+$", text, re.I):
        return "doi"
    return "title"


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/resolve_paper.py '<paper input>'")
        sys.exit(1)

    raw = sys.argv[1].strip()
    kind = classify_input(raw)
    result = {
        "input": raw,
        "kind": kind,
        "canonical_url": raw if kind in {"url", "pdf_url"} else None,
        "pdf_url": raw if kind == "pdf_url" else None,
        "title_guess": raw if kind == "title" else None,
        "doi": raw if kind == "doi" else None,
        "notes": "Use live web search if this metadata is incomplete.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
