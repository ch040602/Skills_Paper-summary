import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from paths import DOWNLOADED_DIR
from source_cache import file_signature, read_json, write_json

CACHE_DIR = str(DOWNLOADED_DIR)
DOWNLOADED_DIR.mkdir(parents=True, exist_ok=True)
HEADERS = {"User-Agent": "PaperSummaryAgent/1.0"}
FETCH_INDEX = ".fetch_index.json"


def safe_name(url: str):
    parsed = urlparse(url)
    stem = (parsed.netloc + parsed.path).replace("/", "_").replace(":", "_")
    return stem[:180] or "paper_source"


def is_pdf_response(resp):
    ctype = (resp.headers.get("Content-Type") or "").lower()
    return "application/pdf" in ctype


def index_path():
    return DOWNLOADED_DIR / FETCH_INDEX


def load_fetch_index():
    return read_json(index_path()) or {}


def save_fetch_index(index):
    write_json(index_path(), index)


def fetch_metadata_path(path):
    source = Path(path)
    return source.with_suffix(source.suffix + ".fetch.json")


def cached_fetch_path(url: str):
    entry = load_fetch_index().get(url)
    if not isinstance(entry, dict):
        return None
    path = entry.get("path")
    if not path:
        return None
    source = Path(path)
    metadata = read_json(fetch_metadata_path(source))
    if not source.exists() or not metadata:
        return None
    if metadata.get("input_url") != url:
        return None
    if metadata.get("source") != file_signature(str(source)):
        return None
    return str(source)


def write_fetch_metadata(url: str, final_url: str, path):
    source = Path(path)
    metadata = {
        "schema_version": 1,
        "input_url": url,
        "final_url": final_url,
        "source": file_signature(str(source)),
    }
    write_json(fetch_metadata_path(source), metadata)
    index = load_fetch_index()
    index[url] = {
        "path": str(source),
        "final_url": final_url,
    }
    save_fetch_index(index)


def fetch_url(url: str, get_fn=requests.get, force: bool = False) -> str:
    if not force:
        cached = cached_fetch_path(url)
        if cached:
            return cached

    resp = get_fn(url, headers=HEADERS, timeout=45, allow_redirects=True)
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
    write_fetch_metadata(url, resp.url, out)
    return str(out)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/fetch_paper.py '<url>'")
        sys.exit(1)

    url = sys.argv[1]
    print(fetch_url(url))


if __name__ == "__main__":
    main()
