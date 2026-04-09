# Paper Summary Agent

`paper-summary-agent` is a skill folder for agent runtimes such as Codex and OpenClaw.

It is designed for paper-reading workflows where the agent receives a paper title, DOI, paper page URL, or direct PDF URL, then resolves the source, fetches text, analyzes the paper, and saves a Korean Markdown report.

## What This Repository Is

This repository is not a standalone web app or CLI product.

It is a portable skill package that provides:

- skill instructions in [`SKILL.md`](./SKILL.md)
- helper prompts in [`resources/agents_append.md`](./resources/agents_append.md)
- utility scripts under [`scripts/`](./scripts/)

In practice, the agent runtime reads `SKILL.md`, decides when to activate the skill, and uses the Python scripts as helpers during execution.

## Intended Use

Use this skill when an agent needs to:

- summarize a paper
- explain a paper
- review a paper
- compare papers
- organize paper notes into Markdown

The skill is written around this workflow:

1. classify the input
2. resolve the canonical source
3. fetch the paper page or PDF
4. extract and normalize text
5. analyze methods and experiments
6. save a Korean Markdown summary
7. optionally extract figures from the PDF and embed them in the report

## Skill Layout

```text
paper-summary-agent/
|-- README.md
|-- SKILL.md
|-- resources/
|   `-- agents_append.md
`-- scripts/
    |-- extract_figures.py
    |-- extract_text.py
    |-- fetch_paper.py
    |-- normalize_text.py
    |-- paths.py
    |-- resolve_paper.py
    `-- save_summary.py
```

## Installing As A Skill

### Codex

Place this folder under your Codex skills directory, for example:

```text
~/.codex/skills/paper-summary-agent
```

Codex can then discover the skill from `SKILL.md`.

### OpenClaw

Install the same folder into the skills location that your OpenClaw setup scans for local skills.

The important requirement is that the folder structure stays intact so the runtime can read:

- `SKILL.md`
- `resources/agents_append.md`
- `scripts/*.py`

If your OpenClaw environment uses a different root directory, copy this entire folder there without flattening it.

## Runtime Outputs

The helper scripts write paper artifacts under:

- `~/Documents/paper-summary-agent/downloaded/`
- `~/Documents/paper-summary-agent/summary/`

These paths are defined in [`scripts/paths.py`](./scripts/paths.py).

## Python Dependencies

Python 3.10+ is recommended.

Install the helper-script dependencies with:

```bash
pip install requests beautifulsoup4 lxml pypdf python-slugify pymupdf pillow
```

These packages are only for the script helpers. The skill logic itself is defined in `SKILL.md`.

## How The Skill Works

The high-level instructions live in [`SKILL.md`](./SKILL.md). The current behavior expects the runtime to:

- accept a title, DOI, URL, or PDF URL
- use live web search when identity resolution is uncertain
- prefer direct PDF or open-access sources
- use subagents for substantial analysis tasks
- save the final report as Korean Markdown

The scripts support that workflow but do not replace the agent runtime.

## Helper Scripts

### `scripts/resolve_paper.py`

Lightweight input classification and metadata scaffolding.

- detects `title`
- detects `doi`
- detects `url`
- detects `pdf_url`

Example:

```bash
python scripts/resolve_paper.py "Attention Is All You Need"
python scripts/resolve_paper.py "10.48550/arXiv.1706.03762"
python scripts/resolve_paper.py "https://arxiv.org/pdf/1706.03762.pdf"
```

### `scripts/fetch_paper.py`

Downloads the resolved URL into the local paper workspace.

- PDFs are saved as `.pdf`
- HTML pages are saved as `.html`

Example:

```bash
python scripts/fetch_paper.py "https://arxiv.org/pdf/1706.03762.pdf"
```

### `scripts/extract_text.py`

Extracts text from downloaded HTML or PDF files and writes a sibling `.txt` file.

### `scripts/normalize_text.py`

Applies lightweight cleanup to extracted text.

### `scripts/extract_figures.py`

Extracts figures from PDFs using caption-based heuristics.

### `scripts/save_summary.py`

Writes the final Markdown summary into the summary output directory and, when a PDF path is provided, injects extracted figures into section `## 8. Figure / table notes`.

## End-To-End Helper Example

```bash
python scripts/resolve_paper.py "https://arxiv.org/pdf/1706.03762.pdf"
python scripts/fetch_paper.py "https://arxiv.org/pdf/1706.03762.pdf"
python scripts/extract_text.py "C:\Users\<user>\Documents\paper-summary-agent\downloaded\arxiv.org_pdf_1706.03762.pdf"
python scripts/normalize_text.py "C:\Users\<user>\Documents\paper-summary-agent\downloaded\arxiv.org_pdf_1706.03762.txt"
python scripts/save_summary.py "Attention Is All You Need" ".\temp_summary.md" "C:\Users\<user>\Documents\paper-summary-agent\downloaded\arxiv.org_pdf_1706.03762.pdf"
```

## Notes

- `SKILL.md` is the primary contract for the agent runtime.
- The repository is meant to be copied as a whole skill folder, not split into individual files.
- `resolve_paper.py` is intentionally simple and does not perform full source resolution by itself.
- Network access is required for `fetch_paper.py`.
- Figure extraction works best on PDFs whose captions follow patterns like `Fig. 1.`.
