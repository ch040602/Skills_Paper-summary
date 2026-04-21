import os
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE_DIR = Path.home() / "Documents" / "paper-summary-agent"
DEFAULT_SUMMARY_DIR = Path.home() / "Desktop" / "obsidian" / "summary_paper"


def resolve_configured_path(raw_value, default_path):
    if not raw_value:
        return default_path

    expanded = Path(os.path.expandvars(os.path.expanduser(raw_value)))
    if expanded.is_absolute():
        return expanded
    return (SKILL_ROOT / expanded).resolve()


BASE_DIR = resolve_configured_path(
    os.environ.get("PAPER_SUMMARY_AGENT_BASE_DIR"),
    DEFAULT_BASE_DIR,
)
DOWNLOADED_DIR = resolve_configured_path(
    os.environ.get("PAPER_SUMMARY_AGENT_DOWNLOAD_DIR"),
    BASE_DIR / "downloaded",
)
SUMMARY_DIR = resolve_configured_path(
    os.environ.get("PAPER_SUMMARY_AGENT_SUMMARY_DIR"),
    DEFAULT_SUMMARY_DIR,
)


def ensure_storage_dirs():
    DOWNLOADED_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
