from pathlib import Path


BASE_DIR = Path.home() / "Documents" / "paper-summary-agent"
DOWNLOADED_DIR = BASE_DIR / "downloaded"
SUMMARY_DIR = BASE_DIR / "summary"


def ensure_storage_dirs():
    DOWNLOADED_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
