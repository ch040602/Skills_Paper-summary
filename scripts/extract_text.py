import os
import sys
from bs4 import BeautifulSoup
from pypdf import PdfReader


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


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/extract_text.py <path>")
        sys.exit(1)

    path = sys.argv[1]
    text = extract_pdf(path) if path.lower().endswith(".pdf") else extract_html(path)
    out = os.path.splitext(path)[0] + ".txt"
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(out)


if __name__ == "__main__":
    main()
