import re
import sys


def normalize(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/normalize_text.py <txt-path>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    text = normalize(text)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(path)


if __name__ == "__main__":
    main()
