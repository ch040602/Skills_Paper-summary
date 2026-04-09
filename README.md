# Paper Summary Agent

`paper-summary-agent` is a local skill folder for Codex-style agent runtimes, including Codex and OpenClaw setups that load skills from a directory on disk.

The main purpose of this repository is simple:

- register the skill under your local `skills` directory
- let the runtime discover `SKILL.md`
- run the skill by giving the agent a paper title, DOI, paper URL, or PDF URL

## Quick Start

1. Put this folder under your runtime's local `skills` directory.
2. Make sure the folder name stays `paper-summary-agent`.
3. Install the Python dependencies used by the helper scripts.
4. Restart or reload the agent runtime if it caches the available skills.
5. Invoke the agent with a paper input or explicitly mention `paper-summary-agent`.

## Repository Role

This repository is a skill package, not a standalone app.

The important files are:

- [`SKILL.md`](./SKILL.md): the runtime-facing instructions
- [`resources/agents_append.md`](./resources/agents_append.md): extra prompt content used by the workflow
- [`scripts/`](./scripts/): helper scripts for fetching papers, extracting text, extracting figures, and saving summaries

## Registering The Skill

### Codex

Clone or copy this repository into the Codex skills directory:

```bash
git clone https://github.com/ch040602/Skills_Paper-summary.git ~/.codex/skills/paper-summary-agent
```

If the folder already exists, update it with:

```bash
git -C ~/.codex/skills/paper-summary-agent pull
```

Codex should then be able to discover the skill from:

```text
~/.codex/skills/paper-summary-agent/SKILL.md
```

If Codex was already running, start a new session or reload the environment so the updated skill list is picked up.

### OpenClaw

Copy or clone the same folder into the skills directory that your OpenClaw deployment scans for local skills.

Example pattern:

```text
<your-openclaw-skills-root>/paper-summary-agent/
```

Required files that must remain together:

- `SKILL.md`
- `resources/agents_append.md`
- `scripts/*.py`

If your OpenClaw setup watches skills only at startup, restart or reload that process after copying the folder.

## Executing The Skill

Once the folder is registered, execute it through the agent runtime rather than by launching this repository directly.

Typical triggers are:

- a paper title
- a DOI
- an arXiv / project / publisher URL
- a direct PDF URL

Example prompts:

```text
Summarize this paper: Attention Is All You Need
```

```text
Read this arXiv paper: https://arxiv.org/pdf/1706.03762.pdf
```

```text
Use paper-summary-agent on DOI 10.48550/arXiv.1706.03762
```

The skill instructions in [`SKILL.md`](./SKILL.md) tell the runtime to:

- resolve the paper identity
- fetch source files
- extract text
- analyze methods and experiments
- save a Korean Markdown report

## Output Locations

During execution, the helper scripts write artifacts to:

- `~/Documents/paper-summary-agent/downloaded/`
- `~/Documents/paper-summary-agent/summary/`

These paths are defined in [`scripts/paths.py`](./scripts/paths.py).

## Python Dependencies

Install the helper-script dependencies before running the skill:

```bash
pip install requests beautifulsoup4 lxml pypdf python-slugify pymupdf pillow
```

These packages are needed for:

- downloading paper pages and PDFs
- extracting text from HTML and PDF
- extracting figures from PDFs
- saving the final Markdown summary

## What Happens At Runtime

The usual execution flow is:

1. the runtime loads `SKILL.md`
2. the user provides a paper-related request
3. the runtime activates `paper-summary-agent`
4. helper scripts under `scripts/` are called as needed
5. the final summary is saved under `~/Documents/paper-summary-agent/summary/`

## Helper Scripts

The repository includes these helpers:

- `scripts/resolve_paper.py`: classifies input as title, DOI, URL, or PDF URL
- `scripts/fetch_paper.py`: downloads the source page or PDF
- `scripts/extract_text.py`: extracts text from downloaded HTML or PDF
- `scripts/normalize_text.py`: cleans extracted text
- `scripts/extract_figures.py`: extracts PDF figures
- `scripts/save_summary.py`: writes the final Markdown summary and embeds figures when available

These are support utilities. The actual skill behavior is defined by `SKILL.md`.

## Updating The Skill

If you already installed the repository as a local skill, update it in place:

```bash
git -C ~/.codex/skills/paper-summary-agent pull
```

Then restart or reload your runtime if skill definitions are cached.

## Notes

- Keep the folder structure intact when copying the skill.
- Do not move `SKILL.md` out of the repository root.
- `resolve_paper.py` is only a lightweight classifier; full source resolution is expected to be handled by the agent workflow.
- `fetch_paper.py` requires network access.
