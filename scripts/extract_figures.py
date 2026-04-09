import re
import sys
from pathlib import Path

import fitz
from PIL import Image, ImageOps


CAPTION_RE = re.compile(r"^Fig\.\s*(\d+)\.\s*(.+)$", re.IGNORECASE)
PAGE_MARGIN = 20.0
TRACK_TOP_MARGIN = 40.0
TRACK_GUTTER = 8.0
CAPTION_GAP = 4.0
CLUSTER_GAP = 10.0
CLIP_PADDING = 8.0
TRIM_PADDING = 12
MIN_RECT_AREA = 8.0
MIN_GROUP_AREA = 600.0
MAX_RENDER_SCALE = 3.0


def rect_area(rect: fitz.Rect) -> float:
    return max(0.0, rect.width) * max(0.0, rect.height)


def normalize_text(text: str) -> str:
    text = text.replace("\ufb01", "fi").replace("\ufb02", "fl")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def caption_track(bbox: fitz.Rect, page_width: float) -> str:
    mid = page_width / 2.0
    if bbox.x1 <= mid + 20.0:
        return "left"
    if bbox.x0 >= mid - 20.0:
        return "right"
    return "full"


def expand_rect(rect: fitz.Rect, padding: float, bounds: fitz.Rect) -> fitz.Rect:
    expanded = fitz.Rect(
        max(bounds.x0, rect.x0 - padding),
        max(bounds.y0, rect.y0 - padding),
        min(bounds.x1, rect.x1 + padding),
        min(bounds.y1, rect.y1 + padding),
    )
    return expanded


def merge_rects(rects, gap: float):
    groups = []
    for rect in sorted(rects, key=lambda item: (item.y0, item.x0)):
        current = fitz.Rect(rect)
        changed = True
        while changed:
            changed = False
            remaining = []
            for group in groups:
                expanded = fitz.Rect(group.x0 - gap, group.y0 - gap, group.x1 + gap, group.y1 + gap)
                if expanded.intersects(current):
                    current |= group
                    changed = True
                else:
                    remaining.append(group)
            groups = remaining
        groups.append(current)
    return groups


def collect_graphic_rects(page):
    rects = []
    text_dict = page.get_text("dict")
    for block in text_dict["blocks"]:
        if block["type"] == 1:
            rect = fitz.Rect(block["bbox"])
            if rect_area(rect) >= MIN_RECT_AREA:
                rects.append(rect)
    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        if not rect:
            continue
        rect = fitz.Rect(rect)
        if rect_area(rect) >= MIN_RECT_AREA:
            rects.append(rect)
    return rects


def collect_captions(page):
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
        match = CAPTION_RE.match(caption_text)
        if not match:
            continue
        bbox = fitz.Rect(block["bbox"])
        captions.append(
            {
                "number": int(match.group(1)),
                "caption": match.group(2).strip(),
                "bbox": bbox,
                "track": caption_track(bbox, page.rect.width),
            }
        )
    return captions


def band_overlap_ratio(rect_a: fitz.Rect, rect_b: fitz.Rect) -> float:
    overlap = max(0.0, min(rect_a.y1, rect_b.y1) - max(rect_a.y0, rect_b.y0))
    min_height = max(1.0, min(rect_a.height, rect_b.height))
    return overlap / min_height


def select_figure_rect(groups, caption_bbox: fitz.Rect, search_rect: fitz.Rect):
    if not groups:
        return None

    def score(rect):
        gap = max(0.0, caption_bbox.y0 - rect.y1)
        return rect_area(rect) - (gap * 50.0)

    ranked = sorted(groups, key=score, reverse=True)
    best = ranked[0]
    selected = []
    for rect in ranked:
        if rect_area(rect) < MIN_GROUP_AREA:
            continue
        if band_overlap_ratio(rect, best) >= 0.35:
            selected.append(rect)
    if not selected:
        selected = [best]

    combined = fitz.Rect(selected[0])
    for rect in selected[1:]:
        combined |= rect

    grown = expand_rect(combined, 24.0, search_rect)
    changed = True
    while changed:
        changed = False
        for rect in groups:
            if rect in selected or rect_area(rect) < MIN_GROUP_AREA:
                continue
            if expand_rect(rect, 12.0, search_rect).intersects(grown):
                combined |= rect
                selected.append(rect)
                grown = expand_rect(combined, 24.0, search_rect)
                changed = True

    return expand_rect(combined, CLIP_PADDING, search_rect)


def trim_whitespace(image: Image.Image) -> Image.Image:
    image = image.convert("RGB")
    grayscale = ImageOps.grayscale(image)
    mask = grayscale.point(lambda value: 255 if value < 245 else 0)
    bbox = mask.getbbox()
    if not bbox:
        return image
    left = max(0, bbox[0] - TRIM_PADDING)
    top = max(0, bbox[1] - TRIM_PADDING)
    right = min(image.width, bbox[2] + TRIM_PADDING)
    bottom = min(image.height, bbox[3] + TRIM_PADDING)
    return image.crop((left, top, right, bottom))


def render_rect(page, rect: fitz.Rect) -> Image.Image:
    pixmap = page.get_pixmap(matrix=fitz.Matrix(MAX_RENDER_SCALE, MAX_RENDER_SCALE), clip=rect, alpha=False)
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    return trim_whitespace(image)


def extract_figures(pdf_path: str, output_dir: str):
    document = fitz.open(pdf_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for stale_path in out_dir.glob("figure_*.png"):
        stale_path.unlink()

    figures = []

    for page_index in range(len(document)):
        page = document[page_index]
        captions = collect_captions(page)
        if not captions:
            continue

        graphics = collect_graphic_rects(page)
        tracks = {"left": TRACK_TOP_MARGIN, "right": TRACK_TOP_MARGIN, "full": TRACK_TOP_MARGIN}

        for track_name in ("left", "right", "full"):
            track_captions = [caption for caption in captions if caption["track"] == track_name]
            track_captions.sort(key=lambda item: item["bbox"].y0)
            if track_name == "left":
                search_x0 = PAGE_MARGIN
                search_x1 = (page.rect.width / 2.0) - TRACK_GUTTER
            elif track_name == "right":
                search_x0 = (page.rect.width / 2.0) + TRACK_GUTTER
                search_x1 = page.rect.width - PAGE_MARGIN
            else:
                search_x0 = PAGE_MARGIN
                search_x1 = page.rect.width - PAGE_MARGIN

            for caption in track_captions:
                search_rect = fitz.Rect(search_x0, tracks[track_name], search_x1, caption["bbox"].y0 - CAPTION_GAP)
                tracks[track_name] = caption["bbox"].y1 + CAPTION_GAP
                if search_rect.is_empty or search_rect.height <= 1.0:
                    continue

                candidate_rects = []
                for graphic in graphics:
                    clipped = graphic & search_rect
                    if clipped.is_empty or rect_area(clipped) < MIN_RECT_AREA:
                        continue
                    candidate_rects.append(clipped)

                groups = merge_rects(candidate_rects, CLUSTER_GAP)
                figure_rect = select_figure_rect(groups, caption["bbox"], search_rect)
                if figure_rect is None:
                    continue

                image = render_rect(page, figure_rect)
                filename = f"figure_{caption['number']:02d}_p{page_index + 1:02d}.png"
                image.save(out_dir / filename, format="PNG")
                figures.append(
                    {
                        "number": caption["number"],
                        "caption": caption["caption"],
                        "filename": filename,
                        "page": page_index + 1,
                        "width": image.width,
                        "height": image.height,
                    }
                )

    figures.sort(key=lambda item: (item["number"], item["page"]))
    return figures


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/extract_figures.py <pdf_path> <output_dir>")
        sys.exit(1)

    figures = extract_figures(sys.argv[1], sys.argv[2])
    for figure in figures:
        print(str(Path(sys.argv[2]) / figure["filename"]))


if __name__ == "__main__":
    main()
