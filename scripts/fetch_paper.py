import sys
from urllib.parse import urlparse

import requests
from paths import DOWNLOADED_DIR

CACHE_DIR = str(DOWNLOADED_DIR)
DOWNLOADED_DIR.mkdir(parents=True, exist_ok=True)
HEADERS = {"User-Agent": "PaperSummaryAgent/1.0"}


def safe_name(url: str):
    parsed = urlparse(url)
    stem = (parsed.netloc + parsed.path).replace("/", "_").replace(":", "_")
    return stem[:180] or "paper_source"


def is_pdf_response(resp):
    ctype = (resp.headers.get("Content-Type") or "").lower()
    return "application/pdf" in ctype


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/fetch_paper.py '<url>'")
        sys.exit(1)

    url = sys.argv[1]
    resp = requests.get(url, headers=HEADERS, timeout=45, allow_redirects=True)
    resp.raise_for_status()

    name = safe_name(resp.url)
    if is_pdf_response(resp) or resp.url.lower().endswith(".pdf"):
        out = DOWNLOADED_DIR / f"{name}.pdf"
        with open(out, "wb") as f:
            f.write(resp.content)
    else:
        out = DOWNLOADED_DIR / f"{name}.html"
        with open(out, "w", encoding="utf-8") as f:
            f.write(resp.text)
    print(str(out))


if __name__ == "__main__":
    main()
