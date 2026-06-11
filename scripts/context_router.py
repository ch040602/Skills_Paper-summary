import json
import re
import sys
from pathlib import Path


SECTION_RE = re.compile(
    r"^(?P<title>(?:\d+(?:\.\d+)?\s+)?(?:Abstract|Introduction|Related Work|Method|Methods|Approach|Model|Training|Inference|Experiments?|Evaluation|Results?|Ablations?|Limitations?|Conclusion).*)$",
    re.IGNORECASE | re.MULTILINE,
)
FIGURE_RE = re.compile(r"\b(?:Fig(?:ure)?\.?)\s*(?P<number>\d+)\s*[:.]\s*(?P<caption>[^\n]+)", re.IGNORECASE)
TABLE_RE = re.compile(r"\bTable\s*(?P<number>[A-Z0-9]+)\s*[:.]\s*(?P<caption>[^\n]+)", re.IGNORECASE)


ROLE_KEYWORDS = {
    "method-analyst": (
        "method",
        "approach",
        "model",
        "training",
        "inference",
        "pipeline",
        "architecture",
        "encoder",
        "decoder",
    ),
    "experiment-analyst": (
        "experiment",
        "evaluation",
        "result",
        "ablation",
        "metric",
        "accuracy",
        "baseline",
        "dataset",
        "split",
    ),
}


def normalize_text(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def trim_to_budget(text: str, char_budget: int) -> str:
    text = normalize_text(text)
    if len(text) <= char_budget:
        return text
    trimmed = text[: max(0, char_budget - 3)].rstrip()
    return trimmed + "..."


def extract_sections(text: str) -> list[dict]:
    matches = list(SECTION_RE.finditer(text))
    if not matches:
        return [{"title": "full_text", "start": 0, "end": len(text), "text": normalize_text(text)}]

    sections = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append(
            {
                "title": match.group("title").strip(),
                "start": start,
                "end": end,
                "text": normalize_text(text[start:end]),
            }
        )
    return sections


def score_section(section: dict, keywords) -> int:
    lowered = f"{section['title']}\n{section['text']}".lower()
    return sum(lowered.count(keyword.lower()) for keyword in keywords)


def context_for_role(sections: list[dict], keywords, char_budget: int) -> str:
    ranked = sorted(sections, key=lambda section: score_section(section, keywords), reverse=True)
    selected = [section for section in ranked if score_section(section, keywords) > 0] or ranked[:1]
    parts = []
    for section in selected:
        candidate = "\n\n".join([*parts, section["text"]]).strip()
        if len(candidate) > char_budget and parts:
            break
        parts.append(section["text"])
        if len("\n\n".join(parts)) >= char_budget:
            break
    return trim_to_budget("\n\n".join(parts), char_budget)


def extract_numbered_items(text: str, pattern: re.Pattern) -> list[dict]:
    items = []
    for match in pattern.finditer(text):
        items.append(
            {
                "number": match.group("number"),
                "caption": normalize_text(match.group("caption")),
                "start": match.start(),
            }
        )
    return items


def build_item_context(label: str, items: list[dict], char_budget: int) -> str:
    lines = [f"{label} {item['number']}. {item['caption']}" for item in items]
    return trim_to_budget("\n".join(lines), char_budget)


def build_context_manifest(text: str, char_budget: int = 12000) -> dict:
    normalized = normalize_text(text)
    sections = extract_sections(normalized)
    figures = extract_numbered_items(normalized, FIGURE_RE)
    tables = extract_numbered_items(normalized, TABLE_RE)

    roles = {
        "resolver": {
            "context": trim_to_budget("\n\n".join(section["text"] for section in sections[:2]), char_budget),
            "inputs": ["metadata", "source_urls", "full_text_availability"],
        },
        "method-analyst": {
            "context": context_for_role(sections, ROLE_KEYWORDS["method-analyst"], char_budget),
            "inputs": ["method_sections", "method_figures"],
        },
        "experiment-analyst": {
            "context": context_for_role(sections, ROLE_KEYWORDS["experiment-analyst"], char_budget),
            "inputs": ["experiment_sections", "tables", "metric_snippets"],
        },
        "figure-analyst": {
            "context": build_item_context("Figure", figures, char_budget),
            "inputs": ["figure_manifest", "caption_context"],
        },
        "table-analyst": {
            "context": build_item_context("Table", tables, char_budget),
            "inputs": ["table_manifest", "table_markdown", "metric_context"],
        },
        "writer": {
            "context": "Use structured outputs from resolver, method-analyst, experiment-analyst, figure-analyst, and table-analyst. Request targeted snippets only for unresolved claims.",
            "inputs": [
                "resolver",
                "method-analyst",
                "experiment-analyst",
                "figure-analyst",
                "table-analyst",
            ],
        },
    }

    return {
        "schema_version": 1,
        "char_budget": char_budget,
        "sections": [
            {"title": section["title"], "start": section["start"], "end": section["end"]}
            for section in sections
        ],
        "figures": figures,
        "tables": tables,
        "roles": roles,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/context_router.py <normalized_txt_path> [char_budget]")
        sys.exit(1)

    path = Path(sys.argv[1])
    char_budget = int(sys.argv[2]) if len(sys.argv) >= 3 else 12000
    text = path.read_text(encoding="utf-8", errors="ignore")
    out = path.with_suffix(".context.json")
    out.write_text(
        json.dumps(build_context_manifest(text, char_budget), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(str(out))


if __name__ == "__main__":
    main()
