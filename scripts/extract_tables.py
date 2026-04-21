import re
import sys

import fitz


TABLE_CAPTION_RE = re.compile(r"^(?:Table)\s+([A-Z0-9]+)\.\s*(.+)$", re.IGNORECASE)
PAGE_MARGIN = 20.0
TRACK_GUTTER = 8.0
MIN_ROWS = 2
MIN_COLS = 2


def normalize_text(text: str) -> str:
    text = text.replace("\ufb01", "fi").replace("\ufb02", "fl")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def table_track(bbox: fitz.Rect, page_width: float) -> str:
    mid = page_width / 2.0
    if bbox.x1 <= mid + 20.0:
        return "left"
    if bbox.x0 >= mid - 20.0:
        return "right"
    return "full"


def collect_table_captions(page):
    captions = []
    text_dict = page.get_text("dict")
    for block in text_dict["blocks"]:
        if block["type"] != 0:
            continue
        text = []
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text.append(span.get("text", ""))
        caption_text = normalize_text("".join(text))
        match = TABLE_CAPTION_RE.match(caption_text)
        if not match:
            continue
        bbox = fitz.Rect(block["bbox"])
        captions.append(
            {
                "number": match.group(1).upper(),
                "caption": match.group(2).strip(),
                "bbox": bbox,
                "track": table_track(bbox, page.rect.width),
            }
        )
    return sorted(captions, key=lambda item: item["bbox"].y0)


def normalize_cell(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = text.replace("\u2013", "-")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def clean_matrix(matrix):
    rows = []
    for row in matrix:
        normalized = [normalize_cell(cell) for cell in row]
        if any(cell for cell in normalized):
            rows.append(normalized)
    if not rows:
        return []

    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]

    keep_columns = []
    for col_idx in range(width):
        if any(row[col_idx] for row in rows):
            keep_columns.append(col_idx)
    if not keep_columns:
        return []

    compact_rows = [[row[idx] for idx in keep_columns] for row in rows]
    return split_multiline_rows(compact_rows)


def split_multiline_rows(rows):
    expanded = []
    for row in rows:
        line_groups = []
        for cell in row:
            if "\n" in cell:
                line_groups.append([part.strip() for part in cell.splitlines()])
            else:
                line_groups.append([cell.strip()])

        meaningful_lengths = {len(group) for group in line_groups if any(item for item in group)}
        if len(meaningful_lengths) == 1 and next(iter(meaningful_lengths)) > 1:
            line_count = next(iter(meaningful_lengths))
            for line_idx in range(line_count):
                expanded.append(
                    [
                        line_groups[col_idx][line_idx].strip() if line_idx < len(line_groups[col_idx]) else ""
                        for col_idx in range(len(line_groups))
                    ]
                )
            continue

        expanded.append([cell.replace("\n", "<br>") for cell in row])

    return expanded


def markdown_escape(cell: str) -> str:
    return cell.replace("|", "\\|").strip() or " "


def matrix_to_markdown(rows):
    if len(rows) < MIN_ROWS or len(rows[0]) < MIN_COLS:
        return ""

    header = [markdown_escape(cell) for cell in rows[0]]
    body = [[markdown_escape(cell) for cell in row] for row in rows[1:]]
    separator = ["---"] * len(header)

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def track_matches(caption_track_name: str, table_track_name: str) -> bool:
    return (
        caption_track_name == "full"
        or table_track_name == "full"
        or caption_track_name == table_track_name
    )


def match_caption(table_bbox: fitz.Rect, table_track_name: str, captions):
    best = None
    best_score = None
    for caption in captions:
        if caption["bbox"].y1 > table_bbox.y0 + 25.0:
            continue
        if not track_matches(caption["track"], table_track_name):
            continue
        vertical_gap = max(0.0, table_bbox.y0 - caption["bbox"].y1)
        x_overlap = max(0.0, min(table_bbox.x1, caption["bbox"].x1) - max(table_bbox.x0, caption["bbox"].x0))
        if caption["track"] != "full" and x_overlap <= 0:
            continue
        score = (vertical_gap * 4.0) - x_overlap
        if best_score is None or score < best_score:
            best = caption
            best_score = score
    return best


def extract_tables(pdf_path: str):
    document = fitz.open(pdf_path)
    extracted = []
    seen = set()

    for page_index, page in enumerate(document):
        captions = collect_table_captions(page)
        if not captions:
            continue

        tables = page.find_tables().tables
        for table in tables:
            bbox = fitz.Rect(table.bbox)
            if bbox.x0 < PAGE_MARGIN and bbox.x1 < PAGE_MARGIN:
                continue

            rows = clean_matrix(table.extract())
            if len(rows) < MIN_ROWS or len(rows[0]) < MIN_COLS:
                continue

            matched_caption = match_caption(bbox, table_track(bbox, page.rect.width), captions)
            if not matched_caption:
                continue

            key = (page_index + 1, matched_caption["number"])
            if key in seen:
                continue
            seen.add(key)

            markdown = matrix_to_markdown(rows)
            if not markdown:
                continue

            extracted.append(
                {
                    "number": matched_caption["number"],
                    "caption": matched_caption["caption"],
                    "page": page_index + 1,
                    "markdown": markdown,
                }
            )

    extracted.sort(key=lambda item: (item["page"], item["number"]))
    return extracted


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/extract_tables.py <pdf_path>")
        sys.exit(1)

    for table in extract_tables(sys.argv[1]):
        print(f"Table {table['number']} (page {table['page']})")
        print(table["caption"])
        print(table["markdown"])
        print()


if __name__ == "__main__":
    main()
