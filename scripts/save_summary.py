import re
import sys
from datetime import datetime
from pathlib import Path

from slugify import slugify

from extract_figures import extract_figures
from paths import SUMMARY_DIR


SECTION_8_RE = re.compile(r"^## 8\. Figure / table notes\s*$", re.MULTILINE)
SECTION_9_RE = re.compile(r"^## 9\.", re.MULTILINE)
FIGURE_NOTE_RE = re.compile(r"^- Fig\.\s*(\d+):\s*(.+)$", re.MULTILINE)
FIGURE_NOTE_BLOCK_RE = re.compile(
    r"^`Fig\.\s*(\d+)`\s*$\n(.*?)(?=^`Fig\.\s*\d+`\s*$|^`Table\s+[A-Z0-9]+`\s*$|^### Table notes\s*$|\Z)",
    re.MULTILINE | re.DOTALL,
)
TABLE_NOTES_RE = re.compile(r"^### Table notes\s*$", re.MULTILINE)
TABLE_NOTE_BLOCK_RE = re.compile(
    r"^`Table\s+([A-Z0-9]+)`\s*$\n(.*?)(?=^`Table\s+[A-Z0-9]+`\s*$|^`Fig\.\s*\d+`\s*$|^### Table notes\s*$|\Z)",
    re.MULTILINE | re.DOTALL,
)


def extract_section_8_parts(content: str):
    match = SECTION_8_RE.search(content)
    if not match:
        return None

    body_start = match.end()
    next_match = SECTION_9_RE.search(content, body_start)
    body_end = next_match.start() if next_match else len(content)
    section_body = content[body_start:body_end].strip()

    figure_notes = {}
    for note_match in FIGURE_NOTE_RE.finditer(section_body):
        figure_notes[int(note_match.group(1))] = note_match.group(2).strip()
    for note_match in FIGURE_NOTE_BLOCK_RE.finditer(section_body):
        note_text = note_match.group(2).strip()
        if note_text:
            figure_notes[int(note_match.group(1))] = note_text

    table_notes = ""
    table_match = TABLE_NOTES_RE.search(section_body)
    if table_match:
        table_notes = section_body[table_match.start():].strip()
    else:
        table_blocks = []
        for note_match in TABLE_NOTE_BLOCK_RE.finditer(section_body):
            table_blocks.append(f"`Table {note_match.group(1)}`\n{note_match.group(2).strip()}")
        if table_blocks:
            table_notes = "### Table notes\n\n" + "\n\n".join(table_blocks)

    return match.start(), body_end, section_body, table_notes, figure_notes


def build_gallery_block(asset_dir_name: str, figures, figure_notes) -> str:
    lines = ["### Figures", ""]
    for figure in figures:
        rel_path = (Path(asset_dir_name) / figure["filename"]).as_posix()
        lines.append(f"### Figure {figure['number']}")
        lines.append("")
        lines.append(f"![Figure {figure['number']}]({rel_path})")
        lines.append(f"Page: {figure['page']}")
        lines.append(f"Caption: {figure['caption']}")
        note = figure_notes.get(figure["number"])
        if note:
            lines.append(f"Explanation: {note}")
        lines.append("")
    return "\n".join(lines).rstrip()


def replace_section_8(content: str, gallery_block: str, table_notes: str) -> str:
    parts = extract_section_8_parts(content)
    if not parts:
        replacement = f"## 8. Figure / table notes\n\n{gallery_block}\n"
        return content.rstrip() + "\n\n" + replacement

    section_start, section_end, _, existing_table_notes, _ = parts
    table_block = table_notes or existing_table_notes
    new_body = gallery_block
    if table_block:
        new_body += "\n\n" + table_block.strip()

    rebuilt = f"## 8. Figure / table notes\n\n{new_body.strip()}\n\n"
    return content[:section_start] + rebuilt + content[section_end:].lstrip("\n")


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/save_summary.py '<title>' '<temp_markdown_path>' [source_pdf_path]")
        sys.exit(1)

    title = sys.argv[1]
    temp_path = sys.argv[2]
    source_path = sys.argv[3] if len(sys.argv) >= 4 else None
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    slug = slugify(title)[:80] or "paper"
    out_path = SUMMARY_DIR / f"{date_str}_{slug}.md"

    with open(temp_path, "r", encoding="utf-8") as file:
        content = file.read()

    section_parts = extract_section_8_parts(content)
    existing_table_notes = ""
    figure_notes = {}
    if section_parts:
        _, _, _, existing_table_notes, figure_notes = section_parts

    if source_path and source_path.lower().endswith(".pdf"):
        asset_dir = SUMMARY_DIR / slug
        figures = extract_figures(source_path, str(asset_dir))
        if figures:
            gallery_block = build_gallery_block(asset_dir.name, figures, figure_notes)
            content = replace_section_8(content, gallery_block, existing_table_notes)

    with open(out_path, "w", encoding="utf-8") as file:
        file.write(content)
    print(str(Path(out_path)))


if __name__ == "__main__":
    main()
