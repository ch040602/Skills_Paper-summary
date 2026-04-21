import re
import sys
from datetime import datetime
from pathlib import Path

from slugify import slugify

from extract_figures import extract_figures
from extract_tables import extract_tables
from paths import SUMMARY_DIR


SECTION_8_RE = re.compile(r"^## 8\. Figure / table notes\s*$", re.MULTILINE)
SECTION_9_RE = re.compile(r"^## 9\.", re.MULTILINE)
SECTION_61_RE = re.compile(r"^### 6\.1 Datasets(?: and evaluation targets)?\s*$", re.MULTILINE)
SECTION_62_RE = re.compile(r"^### 6\.2 Metrics\s*$", re.MULTILINE)
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
SECTION_1_RE = re.compile(r"^## 1\.", re.MULTILINE)
AUTO_TAG_LINE_RE = re.compile(r"^- Auto tags:\s+.*(?:\n|$)", re.MULTILINE)
LEGACY_TAG_LINE_RE = re.compile(r"^Tags:\s+.*(?:\n|$)", re.MULTILINE)
HEADING_RE = re.compile(r"^(#{2,6})\s+(.+?)\s*$", re.MULTILINE)
AUTO_FIGURE_BLOCK_RE = re.compile(
    r"\n*<!-- paper-summary-agent:figures:start -->.*?<!-- paper-summary-agent:figures:end -->\n*",
    re.DOTALL,
)
AUTO_TABLE_BLOCK_RE = re.compile(
    r"\n*<!-- paper-summary-agent:tables:start -->.*?<!-- paper-summary-agent:tables:end -->\n*",
    re.DOTALL,
)
HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")

TOPIC_RULES = [
    ("computer_vision", ("segmentation", "detector", "object detection", "mask", "panoptic", "coco", "lvis", "ego4d", "sam")),
    ("dataset", ("dataset", "annotation", "sa-1b", "paco", "coco-rem")),
    ("benchmark", ("benchmark", "evaluate", "evaluation", "coco-rem")),
    ("segmentation", ("segmentation", "mask", "sa-1b")),
    ("panoptic_segmentation", ("panoptic segmentation",)),
    ("part_segmentation", ("part segmentation", "object-part", "part mask")),
    ("attribute_prediction", ("attribute prediction", "object attribute", "part attribute")),
    ("zero_shot_detection", ("zero-shot instance detection", "zero-shot detection")),
    ("instance_retrieval", ("instance detection", "instance retrieval", "few-shot instance")),
    ("object_detection", ("object detector", "object detection", "detector")),
    ("foundation_model", ("foundation model", "segment anything", "sam")),
    ("promptable_segmentation", ("promptable segmentation",)),
    ("llm", ("large language model", "llm", "language model")),
    ("reasoning", ("reasoning", "reason in a continuous latent space", "chain of continuous thought")),
    ("latent_reasoning", ("continuous latent", "coconut", "latent space")),
    ("mobile_security", ("smartphone", "authentication", "mobile computing", "pin")),
    ("biometrics", ("biometric", "tap biometrics")),
    ("smartphone_authentication", ("smartphone", "pin authentication", "tapin")),
]

SPECIAL_TAGS_BY_TITLE = {
    "benchmarking object detectors with coco: a new path forward": [
        "computer_vision",
        "object_detection",
        "benchmark",
        "dataset",
        "instance_segmentation",
        "coco",
    ],
    "paco: parts and attributes of common objects": [
        "computer_vision",
        "dataset",
        "benchmark",
        "part_segmentation",
        "attribute_prediction",
        "zero_shot_detection",
        "instance_retrieval",
    ],
    "panoptic segmentation": [
        "computer_vision",
        "segmentation",
        "panoptic_segmentation",
        "benchmark",
        "evaluation_metric",
    ],
    "segment anything": [
        "computer_vision",
        "segmentation",
        "foundation_model",
        "promptable_segmentation",
        "dataset",
        "zero_shot_transfer",
    ],
    "visual recognition by request": [
        "computer_vision",
        "segmentation",
        "hierarchical_segmentation",
        "part_segmentation",
        "open_vocabulary_recognition",
    ],
    "training large language models to reason in a continuous latent space": [
        "llm",
        "reasoning",
        "latent_reasoning",
        "continuous_latent_space",
        "coconut",
    ],
    "tapin: reinforcing pin authentication on smartphones with tap biometrics": [
        "mobile_security",
        "smartphone_authentication",
        "biometrics",
        "tap_biometrics",
        "authentication",
    ],
}

KNOWN_VENUES = [
    "IEEE Transactions on Mobile Computing",
    "CVPR",
    "ICCV",
    "ECCV",
    "NeurIPS",
    "ICLR",
    "ICML",
    "ACL",
    "EMNLP",
    "NAACL",
    "AAAI",
]

INLINE_FIGURE_TARGETS = {
    "core_idea": {
        "pattern": re.compile(r"^## 4\. Core idea\s*$", re.MULTILINE),
        "label": "4. Core idea",
    },
    "method_overall": {
        "pattern": re.compile(r"^### 5\.1 Overall pipeline\s*$", re.MULTILINE),
        "label": "5.1 Overall pipeline",
    },
    "method_modules": {
        "pattern": re.compile(r"^### 5\.2 Main modules\s*$", re.MULTILINE),
        "label": "5.2 Main modules",
    },
    "training_inference": {
        "pattern": re.compile(r"^### 5\.3 Training / inference details\s*$", re.MULTILINE),
        "label": "5.3 Training / inference details",
    },
    "datasets": {
        "pattern": SECTION_61_RE,
        "label": "6.1 Datasets and evaluation targets",
    },
    "baselines": {
        "pattern": re.compile(r"^### 6\.3 Baselines\s*$", re.MULTILINE),
        "label": "6.3 Baselines",
    },
    "main_results": {
        "pattern": re.compile(r"^## 7\. Main results\s*$", re.MULTILINE),
        "label": "7. Main results",
    },
}


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


def extract_table_notes_map(content: str) -> dict[str, str]:
    notes = {}
    for note_match in TABLE_NOTE_BLOCK_RE.finditer(content):
        note_text = note_match.group(2).strip()
        if note_text:
            notes[note_match.group(1).upper()] = note_text
    return notes


def build_gallery_block(asset_dir_name: str, figures, figure_notes) -> str:
    lines = ["### Figures", ""]
    for figure in figures:
        rel_path = (Path(asset_dir_name) / figure["filename"]).as_posix()
        lines.append(f"### Figure {figure['number']}")
        lines.append("")
        lines.append(f"![Figure {figure['number']}]({rel_path})")
        note = normalize_note_text(figure_notes.get(figure["number"], ""))
        lines.append(note or "Korean figure explanation required.")
        lines.append("")
    return "\n".join(lines).rstrip()


def strip_auto_figure_blocks(content: str) -> str:
    cleaned = AUTO_FIGURE_BLOCK_RE.sub("\n\n", content)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip() + "\n"


def strip_auto_table_blocks(content: str) -> str:
    cleaned = AUTO_TABLE_BLOCK_RE.sub("\n\n", content)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip() + "\n"


def normalize_note_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def markdown_to_text(text: str) -> str:
    flattened = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    flattened = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", flattened)
    flattened = flattened.replace("`", " ")
    flattened = re.sub(r"^[#>*-]+\s*", "", flattened, flags=re.MULTILINE)
    return normalize_note_text(flattened)


def contains_any(text: str, keywords) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def get_section_body(content: str, heading_pattern) -> str:
    match = heading_pattern.search(content)
    if not match:
        return ""

    bounds = find_heading_bounds(content, heading_pattern)
    if not bounds:
        return ""

    return content[match.end():bounds["end"]].strip()


def note_looks_like_caption(note_text: str, caption_text: str) -> bool:
    normalized_note = markdown_to_text(note_text).lower()
    normalized_caption = markdown_to_text(caption_text).lower()
    if not normalized_note or not normalized_caption:
        return False

    return (
        normalized_note == normalized_caption
        or normalized_note == f"caption: {normalized_caption}"
        or normalized_note == f"original caption: {normalized_caption}"
    )


def validate_experiment_sections(content: str):
    errors = []

    datasets_body = markdown_to_text(get_section_body(content, SECTION_61_RE))
    if not datasets_body:
        errors.append("Missing section `6.1 Datasets and evaluation targets`.")
    else:
        if len(datasets_body) < 80:
            errors.append("Section `6.1` is too short. Explain datasets plus the evaluation targets.")
        if not contains_any(
            datasets_body,
            (
                "\ud3c9\uac00 \ub300\uc0c1",
                "\uc608\uce21 \ub300\uc0c1",
                "\uc608\uce21 \ub2e8\uc704",
                "task",
                "tasks",
                "\uacfc\uc81c \uc124\uc815",
                "\ubd84\ud560",
                "split",
                "zero-shot",
                "few-shot",
                "\uac80\ucd9c",
                "\ubd84\ub958",
                "\uc138\uadf8\uba58\ud14c\uc774\uc158",
                "retrieval",
                "generation",
            ),
        ):
            errors.append("Section `6.1` must clearly state what is evaluated or predicted, not only dataset names.")

    metrics_body = markdown_to_text(get_section_body(content, SECTION_62_RE))
    if not metrics_body:
        errors.append("Missing section `6.2 Metrics`.")
    else:
        if len(metrics_body) < 100:
            errors.append("Section `6.2` is too short. Define the main metrics instead of only listing their names.")
        if not contains_any(
            metrics_body,
            (
                "\uc815\uc758",
                "\uc758\ubbf8",
                "\ud574\uc11d",
                "\uce21\uc815",
                "\uacc4\uc0b0",
                "\uc0b0\ucd9c",
                "\ub192\uc744\uc218\ub85d",
                "\ub0ae\uc744\uc218\ub85d",
                "higher is better",
                "lower is better",
                "threshold",
                "average",
                "averaged",
            ),
        ):
            errors.append("Section `6.2` must define how the metrics work and how to interpret them.")

    if errors:
        raise ValueError("Summary validation failed before saving:\n- " + "\n- ".join(errors))


def validate_figure_notes(figures, figure_notes):
    missing = []
    non_korean = []
    caption_like = []
    too_short = []

    for figure in figures:
        number = figure["number"]
        note = normalize_note_text(figure_notes.get(number, ""))
        if not note:
            missing.append(number)
            continue

        note_text = markdown_to_text(note)
        if len(note_text) < 25:
            too_short.append(number)
        if not HANGUL_RE.search(note_text):
            non_korean.append(number)
        if note_looks_like_caption(note_text, figure.get("caption", "")):
            caption_like.append(number)

    errors = []
    if missing:
        errors.append(f"Missing Korean explanations for figures: {', '.join(map(str, missing))}.")
    if non_korean:
        errors.append(f"Figure notes must be written in Korean for figures: {', '.join(map(str, non_korean))}.")
    if caption_like:
        errors.append(f"Figure notes look like raw captions instead of Korean explanations for figures: {', '.join(map(str, caption_like))}.")
    if too_short:
        errors.append(f"Figure notes are too short to be useful for figures: {', '.join(map(str, too_short))}.")

    if errors:
        raise ValueError("Figure note validation failed before saving:\n- " + "\n- ".join(errors))


def choose_figure_target(figure) -> str | None:
    text = normalize_note_text(f"{figure.get('caption', '')} {figure.get('note', '')}".lower())

    rules = [
        (
            "baselines",
            [
                "few-shot instance detection model",
                "embedding model",
                "2-tower",
                "two-tower",
                "arcface",
                "baseline",
            ],
        ),
        (
            "main_results",
            [
                "qualitative prediction",
                "prediction examples",
                "zero-shot과 few-shot",
                "zero-shot and few-shot",
                "compare",
                "comparison",
                "performance",
                "result",
                "한계를 강조",
            ],
        ),
        (
            "core_idea",
            [
                "conceptual overview",
                "전체 문제 설정",
                "문제 설정",
                "instance query",
                "instance queries",
                "query setting",
                "overview",
                "annotation structure",
            ],
        ),
        (
            "datasets",
            [
                "dataset statistics",
                "distribution",
                "분포",
                "통계",
                "instances across",
                "size distribution",
                "75 object categories",
            ],
        ),
        (
            "method_modules",
            [
                "vocabulary",
                "taxonomy",
                "annotation",
                "attribute head",
                "model adds",
                "구조도",
                "quality",
                "mio",
                "parts of",
                "manually defined parts",
                "reference image",
                "subset of attributes",
            ],
        ),
    ]

    for target_key, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return target_key

    return None


def find_heading_bounds(content: str, heading_pattern):
    match = heading_pattern.search(content)
    if not match:
        return None

    heading_line = content[match.start():match.end()]
    level_match = re.match(r"^(#+)", heading_line)
    if not level_match:
        return None
    level = len(level_match.group(1))

    section_end = len(content)
    for next_match in HEADING_RE.finditer(content, match.end()):
        next_level = len(next_match.group(1))
        if next_level <= level:
            section_end = next_match.start()
            break

    return {
        "start": match.start(),
        "end": section_end,
        "level": level,
    }


def build_inline_figure_block(asset_dir_name: str, figures, heading_level: int) -> str:
    related_heading = "#" * min(heading_level + 1, 6)
    lines = [
        "<!-- paper-summary-agent:figures:start -->",
        f"{related_heading} Related Figures",
        "",
    ]
    for figure in figures:
        rel_path = (Path(asset_dir_name) / figure["filename"]).as_posix()
        lines.append(f"**Figure {figure['number']}**")
        lines.append("")
        lines.append(f"![Figure {figure['number']}]({rel_path})")
        lines.append(figure.get("note") or "Korean figure explanation required.")
        lines.append("")
    lines.append("<!-- paper-summary-agent:figures:end -->")
    return "\n".join(lines).rstrip()


def build_inline_table_block(tables, table_notes_map, heading_level: int) -> str:
    related_heading = "#" * min(heading_level + 1, 6)
    lines = [
        "<!-- paper-summary-agent:tables:start -->",
        f"{related_heading} Related Tables",
        "",
    ]
    for table in tables:
        title = normalize_note_text(table.get("caption", ""))
        lines.append(f"**Table {table['number']}. {title}**")
        lines.append("")
        lines.append(table.get("markdown", "").strip() or "| Extraction failed | |")
        note = normalize_note_text(table_notes_map.get(str(table["number"]).upper(), ""))
        if note:
            lines.append("")
            lines.append(note)
        lines.append("")
    lines.append("<!-- paper-summary-agent:tables:end -->")
    return "\n".join(lines).rstrip()


def inject_figures_into_sections(content: str, asset_dir_name: str, figures, figure_notes):
    content = strip_auto_figure_blocks(content)

    enriched_figures = []
    placements = []
    for figure in figures:
        note = normalize_note_text(figure_notes.get(figure["number"], ""))
        enriched = dict(figure)
        enriched["note"] = note
        enriched["target_key"] = choose_figure_target(enriched)
        enriched_figures.append(enriched)

    grouped = {}
    leftovers = []
    for figure in enriched_figures:
        target_key = figure["target_key"]
        if not target_key or target_key not in INLINE_FIGURE_TARGETS:
            leftovers.append(figure)
            continue
        grouped.setdefault(target_key, []).append(figure)

    insertions = []
    for target_key, grouped_figures in grouped.items():
        bounds = find_heading_bounds(content, INLINE_FIGURE_TARGETS[target_key]["pattern"])
        if not bounds:
            leftovers.extend(grouped_figures)
            continue
        block = build_inline_figure_block(asset_dir_name, grouped_figures, bounds["level"])
        insertions.append((bounds["end"], block))
        for figure in grouped_figures:
            placements.append(
                {
                    "number": figure["number"],
                    "target_label": INLINE_FIGURE_TARGETS[target_key]["label"],
                    "note": figure.get("note", "") or normalize_note_text(figure.get("caption", "")),
                }
            )

    for position, block in sorted(insertions, key=lambda item: item[0], reverse=True):
        content = content[:position].rstrip() + "\n\n" + block + "\n\n" + content[position:].lstrip("\n")

    placements.sort(key=lambda item: item["number"])
    leftovers.sort(key=lambda item: item["number"])
    return content, placements, leftovers


def inject_tables_into_sections(content: str, tables, table_notes_map):
    content = strip_auto_table_blocks(content)
    if not tables:
        return content, []

    bounds = find_heading_bounds(content, INLINE_FIGURE_TARGETS["main_results"]["pattern"])
    if not bounds:
        return content, []

    block = build_inline_table_block(tables, table_notes_map, bounds["level"])
    content = content[:bounds["end"]].rstrip() + "\n\n" + block + "\n\n" + content[bounds["end"]:].lstrip("\n")
    placements = [
        {
            "number": str(table["number"]).upper(),
            "target_label": INLINE_FIGURE_TARGETS["main_results"]["label"],
            "note": normalize_note_text(table_notes_map.get(str(table["number"]).upper(), "")),
        }
        for table in tables
    ]
    return content, placements


def build_section_8_index(placements, leftovers, table_placements, table_notes: str) -> str:
    lines = ["## 8. Figure / table notes", ""]

    if placements:
        lines.extend(["### Figure placement", ""])
        for placement in placements:
            note = placement["note"] or "See the inline figure explanation in the linked section."
            lines.append(
                f"- `Fig. {placement['number']}` -> `{placement['target_label']}`: {note}"
            )
        lines.append("")

    if table_placements:
        lines.extend(["### Table placement", ""])
        for placement in table_placements:
            note = placement["note"] or "See the inline table explanation in the linked section."
            lines.append(
                f"- `Table {placement['number']}` -> `{placement['target_label']}`: {note}"
            )
        lines.append("")

    if leftovers:
        lines.extend(["### Additional figure notes", ""])
        for figure in leftovers:
            note = figure.get("note") or "Korean figure explanation required."
            lines.append(f"- `Fig. {figure['number']}`: {note}")
        lines.append("")

    if table_notes:
        lines.append(table_notes.strip())
    else:
        lines.extend(["### Table notes", "", "- No table notes available."])

    return "\n".join(lines).rstrip() + "\n"


def replace_section_8_with_index(content: str, placements, leftovers, table_placements, table_notes: str) -> str:
    new_section = build_section_8_index(placements, leftovers, table_placements, table_notes)
    parts = extract_section_8_parts(content)
    if not parts:
        return content.rstrip() + "\n\n" + new_section

    section_start, section_end, _, existing_table_notes, _ = parts
    effective_table_notes = table_notes or existing_table_notes
    rebuilt = build_section_8_index(placements, leftovers, table_placements, effective_table_notes)
    return content[:section_start] + rebuilt + content[section_end:].lstrip("\n")


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


def slugify_tag(text: str) -> str:
    slug = slugify(text, separator="_")
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug


def extract_title(content: str, fallback_title: str = "") -> str:
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip().strip("`")
    return fallback_title.strip().strip("`")


def find_metadata_value(content: str, labels) -> str | None:
    if isinstance(labels, str):
        labels = [labels]
    for line in content.splitlines():
        stripped = line.strip()
        for label in labels:
            prefix = f"- {label}:"
            if stripped.startswith(prefix):
                return stripped[len(prefix):].strip().strip("`")
    return None


def infer_year(content: str) -> str | None:
    priority_labels = [
        "Issue publication date",
        "Issue publication year",
        "호 발행일",
        "Online publication date",
        "온라인 공개일",
        "Date on paper",
        "Release date",
        "arXiv page metadata date",
        "공개일",
        "Publication year",
        "Published in",
    ]
    for label in priority_labels:
        value = find_metadata_value(content, label)
        if not value:
            continue
        match = re.search(r"(?<!\d)(20\d{2})(?!\d)", value)
        if match:
            return match.group(1)

    for line in content.splitlines():
        if "CVPR" in line or "ICCV" in line or "ECCV" in line or "NeurIPS" in line or "ICLR" in line:
            match = re.search(r"(?<!\d)(20\d{2})(?!\d)", line)
            if match:
                return match.group(1)

    return None


def infer_venue(content: str) -> str | None:
    venue = find_metadata_value(content, ["Venue", "Venue / status", "Journal", "Conference", "Published in", "저널", "학회"])
    if venue:
        if "arxiv" in venue.lower():
            return "arXiv"
        return venue

    status = find_metadata_value(content, "상태")
    if status and "arxiv" in status.lower():
        return "arXiv"

    if find_metadata_value(content, ["arXiv", "식별자", "arXiv ID / version"]):
        return "arXiv"

    canonical_url = find_metadata_value(content, "Canonical URL") or ""
    if "arxiv.org" in canonical_url.lower():
        return "arXiv"

    for known_venue in KNOWN_VENUES:
        if re.search(rf"\b{re.escape(known_venue)}\b", content, re.IGNORECASE):
            return known_venue

    if re.search(r"\bCVPR\s+20\d{2}\b", content):
        return "CVPR"

    return None


def infer_topic_tags(title: str, content: str) -> list[str]:
    tags = []
    section_8_match = SECTION_8_RE.search(content)
    tag_source = content[:section_8_match.start()] if section_8_match else content[:8000]
    lowered = f"{title}\n{tag_source}".lower()

    special = SPECIAL_TAGS_BY_TITLE.get(title.lower())
    if special:
        tags.extend(special)
    else:
        for tag, keywords in TOPIC_RULES:
            if any(keyword_matches(lowered, keyword) for keyword in keywords):
                tags.append(tag)

    deduped = []
    for tag in tags:
        if tag not in deduped:
            deduped.append(tag)
    return deduped


def keyword_matches(text: str, keyword: str) -> bool:
    pieces = [re.escape(piece) for piece in keyword.lower().split()]
    pattern = r"\b" + r"\s+".join(pieces) + r"\b"
    return re.search(pattern, text) is not None


def build_tag_line(content: str, fallback_title: str = "") -> str:
    title = extract_title(content, fallback_title)
    tags = infer_topic_tags(title, content)

    venue = infer_venue(content)
    year = infer_year(content)
    if venue and year:
        venue_tag = slugify_tag(venue)
        if venue_tag:
            year_suffix = f"_{year}"
            base_venue_tag = venue_tag[:-len(year_suffix)] if venue_tag.endswith(year_suffix) else venue_tag
            base_venue_tag = base_venue_tag or venue_tag
            tags.append(f"{base_venue_tag}_{year}")
            tags.append(base_venue_tag)
        tags.append(year)

    deduped = []
    for tag in tags:
        if tag not in deduped:
            deduped.append(tag)

    formatted = " ".join(f"#{tag}" for tag in deduped)
    return f"- Auto tags: {formatted}".rstrip()


def upsert_tags(content: str, fallback_title: str = "") -> str:
    tag_line = build_tag_line(content, fallback_title)
    if AUTO_TAG_LINE_RE.search(content):
        return AUTO_TAG_LINE_RE.sub(tag_line + "\n", content, count=1)
    if LEGACY_TAG_LINE_RE.search(content):
        return LEGACY_TAG_LINE_RE.sub(tag_line + "\n", content, count=1)

    metadata_line = re.search(r"^- Full text availability:.*$", content, re.MULTILINE)
    if metadata_line:
        insert_at = metadata_line.end()
        return content[:insert_at].rstrip() + "\n" + tag_line + "\n" + content[insert_at:]

    section_match = SECTION_1_RE.search(content)
    if section_match:
        return content[:section_match.start()].rstrip() + "\n\n" + tag_line + "\n\n" + content[section_match.start():]

    return content.rstrip() + "\n\n" + tag_line + "\n"


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

    validate_experiment_sections(content)

    section_parts = extract_section_8_parts(content)
    existing_table_notes = ""
    table_notes_map = {}
    figure_notes = {}
    if section_parts:
        _, _, section_8_body, existing_table_notes, figure_notes = section_parts
        table_notes_map = extract_table_notes_map(section_8_body)

    if source_path and source_path.lower().endswith(".pdf"):
        asset_dir = SUMMARY_DIR / slug
        figures = extract_figures(source_path, str(asset_dir))
        tables = extract_tables(source_path)
        table_placements = []
        if tables:
            content, table_placements = inject_tables_into_sections(content, tables, table_notes_map)
        if figures:
            validate_figure_notes(figures, figure_notes)
            content, placements, leftovers = inject_figures_into_sections(
                content, asset_dir.name, figures, figure_notes
            )
            content = replace_section_8_with_index(
                content, placements, leftovers, table_placements, existing_table_notes
            )
        elif tables:
            content = replace_section_8_with_index(
                content, [], [], table_placements, existing_table_notes
            )

    content = upsert_tags(content, title)

    with open(out_path, "w", encoding="utf-8") as file:
        file.write(content)
    print(str(Path(out_path)))


if __name__ == "__main__":
    main()
