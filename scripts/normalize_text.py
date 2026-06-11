import re
import sys
from pathlib import Path

from source_cache import file_signature, read_json, write_json


def normalize(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def normalize_metadata_path(path: str):
    source = Path(path)
    return source.with_suffix(source.suffix + ".normalize.json")


def normalize_file(path: str) -> str:
    metadata_path = normalize_metadata_path(path)
    before_signature = file_signature(path)
    metadata = read_json(metadata_path)
    if (
        metadata
        and metadata.get("schema_version") == 1
        and metadata.get("output") == before_signature
    ):
        return path

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    normalized = normalize(text)
    if normalized != text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(normalized)
    write_json(
        metadata_path,
        {
            "schema_version": 1,
            "input": before_signature,
            "output": file_signature(path),
            "normalizer": "normalize_text.v1",
        },
    )
    return path


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/normalize_text.py <txt-path>")
        sys.exit(1)

    print(normalize_file(sys.argv[1]))


if __name__ == "__main__":
    main()
