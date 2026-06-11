import hashlib
import json
from pathlib import Path


CACHE_FILENAME = ".paper_summary_assets.json"
CACHE_SCHEMA_VERSION = 2
EXTRACTOR_SIGNATURE = {
    "asset_cache": CACHE_SCHEMA_VERSION,
    "figures": "extract_figures.v1",
    "tables": "extract_tables.v1",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_signature(pdf_path: str) -> dict:
    path = Path(pdf_path)
    stat = path.stat()
    return {
        "path": str(path.resolve()),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": file_sha256(path),
    }


def cache_path_for(asset_dir: str) -> Path:
    return Path(asset_dir) / CACHE_FILENAME


def figure_files_exist(asset_dir: str, figures) -> bool:
    base = Path(asset_dir)
    for figure in figures:
        filename = figure.get("filename")
        if filename and not (base / filename).exists():
            return False
    return True


def read_cache(asset_dir: str):
    cache_path = cache_path_for(asset_dir)
    if not cache_path.exists():
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return None


def write_cache(asset_dir: str, signature: dict, figures, tables) -> None:
    cache_path = cache_path_for(asset_dir)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "source": signature,
        "extractor": EXTRACTOR_SIGNATURE,
        "figures": figures,
        "tables": tables,
    }
    with open(cache_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def load_or_extract_pdf_assets(pdf_path: str, asset_dir: str, extract_figures_fn, extract_tables_fn):
    signature = source_signature(pdf_path)
    Path(asset_dir).mkdir(parents=True, exist_ok=True)
    cache = read_cache(asset_dir)
    if (
        cache
        and cache.get("schema_version") == CACHE_SCHEMA_VERSION
        and cache.get("source") == signature
        and cache.get("extractor") == EXTRACTOR_SIGNATURE
        and isinstance(cache.get("figures"), list)
        and isinstance(cache.get("tables"), list)
        and figure_files_exist(asset_dir, cache.get("figures", []))
    ):
        return cache.get("figures", []), cache.get("tables", [])

    figures = extract_figures_fn(pdf_path, asset_dir)
    tables = extract_tables_fn(pdf_path)
    write_cache(asset_dir, signature, figures, tables)
    return figures, tables
