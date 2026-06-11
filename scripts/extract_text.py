import os
import sys
from bs4 import BeautifulSoup
from pypdf import PdfReader
from source_cache import file_signature, read_json, write_json


def extract_pdf(path: str) -> str:
    reader = PdfReader(path)
    texts = []
    for page in reader.pages:
        try:
            texts.append(page.extract_text() or "")
        except Exception:
            texts.append("")
    return "\n".join(texts)


def extract_html(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)


def extract_metadata_path(path: str):
    return os.path.splitext(path)[0] + ".txt.extract.json"


def extract_to_text_file(path: str, pdf_extractor=extract_pdf, html_extractor=extract_html) -> str:
    out = os.path.splitext(path)[0] + ".txt"
    metadata_path = extract_metadata_path(path)
    signature = file_signature(path)
    metadata = read_json(metadata_path)
    if (
        os.path.exists(out)
        and metadata
        and metadata.get("schema_version") == 1
        and metadata.get("source") == signature
    ):
        return out

    is_pdf = path.lower().endswith(".pdf")
    text = pdf_extractor(path) if is_pdf else html_extractor(path)
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    write_json(
        metadata_path,
        {
            "schema_version": 1,
            "source": signature,
            "output": file_signature(out),
            "extractor": "pdf" if is_pdf else "html",
        },
    )
    return out


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/extract_text.py <path>")
        sys.exit(1)

    print(extract_to_text_file(sys.argv[1]))


if __name__ == "__main__":
    main()
