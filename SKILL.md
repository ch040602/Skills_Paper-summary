---
name: paper-summary-agent
description: Resolve a paper from title, DOI, paper page URL, or direct PDF URL; fetch available source text; use the latest available frontier subagents for deep method and experiment analysis; then save a comprehensive Korean Markdown summary.
---

# Purpose

Use this skill whenever the user asks to summarize, review, analyze, compare, or organize an academic paper, preprint, technical report, or benchmark paper.

# Required behavior

1. Accept any of the following inputs:
   - paper title
   - DOI
   - arXiv / OpenReview / CVF / ACM / IEEE / Springer / Semantic Scholar / project page URL
   - direct PDF URL
2. Use live web search when the paper identity or canonical source is uncertain.
3. Prefer the best available source in this order:
   - direct PDF URL
   - open-access paper page with PDF
   - canonical abstract/paper page
   - metadata-only page
4. Save fetched source files in the configured download directory from `scripts/paths.py` (default: `~/Documents/paper-summary-agent/downloaded/`).
5. When a PDF source is available, extract embedded figures into `<summary_dir>/<slugified_title>/`, where `<summary_dir>` is the configured Obsidian summary directory from `scripts/paths.py`, recover full-width / two-column figures as cleanly as possible, and embed them in the final Markdown so the figures render directly in the report.
6. When a PDF source is available, also extract major tables and render them as Markdown tables inside the final report instead of leaving them as prose-only notes.
7. Use subagents explicitly for non-trivial paper tasks:
   - `resolver` for identity resolution and source gathering
   - `method-analyst` for architecture/method details
   - `experiment-analyst` for datasets, metrics, results, and limitations
   - `figure-analyst` for Korean explanations of extracted figures
   - `table-analyst` for Korean explanations of extracted tables and metric interpretation
   - `writer` for final Korean Markdown synthesis
8. Final output file must be a Korean Markdown file saved to the configured Obsidian summary directory (`PAPER_SUMMARY_AGENT_SUMMARY_DIR`; default: `~/Desktop/obsidian/summary_paper/`).
9. Agent-facing instructions, filenames, code comments, and internal templates should remain in English unless Korean is necessary in the final report.
10. If full text cannot be obtained, still produce the summary and clearly mark `Full text unavailable` near the top.
11. Avoid unsupported claims. Distinguish observed facts from inference.
12. Keep long verbatim quotes to a minimum.
13. By default, use the latest available frontier model for paper-analysis subagents. Prefer `gpt-5.4` with `high` or `xhigh` reasoning effort for `method-analyst`, `experiment-analyst`, `figure-analyst`, `table-analyst`, and `writer`, unless the user explicitly asks for a faster/cheaper option.
14. Default to a thorough report rather than a brief summary. Do not stop at a high-level abstract-style overview when the full text is available.
15. The experiment analysis must explicitly cover:
   - evaluation targets: what is predicted / classified / retrieved / segmented, the unit of evaluation, and the task setting or split
   - evaluation metrics, how each metric is defined or computed, and how higher/lower values should be interpreted
   - evaluation protocol and training/inference setup
   - main quantitative results
   - ablations, efficiency measurements, and limitations
   - figure-by-figure and table-by-table notes for the main paper, plus important appendix tables/figures when relevant
16. Every extracted figure used in the report must have a Korean explanation based on the paper's content, and those explanations should be drafted from the `figure-analyst` subagent output. Do not use the raw English caption as the main figure description.
17. Every extracted table rendered in the report must be accompanied by a Korean explanation and metric-reading guidance based on the `table-analyst` subagent output.
18. Insert automatically generated topic / venue tags near the metadata block in the final Markdown.
19. If the first analysis pass is missing evaluation targets, metric definitions, protocol details, or important figure/table explanations, do a second pass before writing the final report.

# Workflow

## Step 1: Interpret input

Classify the input as one of:
- `title`
- `doi`
- `url`
- `pdf_url`

If ambiguous, search the web before proceeding.

## Step 2: Resolve canonical source

Run:
- `python scripts/resolve_paper.py "<INPUT>"`

This produces candidate metadata. If the result is weak or incomplete, improve it with live web search.

## Step 3: Fetch source

When a usable URL exists, run:
- `python scripts/fetch_paper.py "<URL>"`

Then extract text:
- `python scripts/extract_text.py <FETCHED_PATH>`
- `python scripts/normalize_text.py <TXT_PATH>`

## Step 4: Delegate to subagents

For substantial paper analysis, explicitly create subagents:

- `resolver`
  - confirm canonical title
  - list source URLs
  - note whether PDF/full text was obtained
- `method-analyst`
  - use the latest available frontier model, preferably `gpt-5.4`
  - identify problem, main idea, model/pipeline, latent-vs-language mechanics, training/inference details
  - explain the role of key method figures and any probing setup used for interpretation
- `experiment-analyst`
  - use the latest available frontier model, preferably `gpt-5.4`
  - identify datasets, evaluation targets, metrics, metric definitions, evaluation protocol, baselines, main tables/figures, appendix evidence, ablations, efficiency, failure modes, and limitations
- `figure-analyst`
  - use the latest available frontier model, preferably `gpt-5.4`
  - write Korean explanations for each extracted figure
  - explicitly explain what the reader should focus on, how to read the figure, and why it matters
- `table-analyst`
  - use the latest available frontier model, preferably `gpt-5.4`
  - write Korean explanations for each extracted table
  - explain what each metric measures, how to read the rows / columns, and the main takeaway
- `writer`
  - use the latest available frontier model, preferably `gpt-5.4`
  - synthesize the final Korean Markdown file using the required template
  - integrate the outputs from `figure-analyst` and `table-analyst`
  - for each extracted figure, write 2-4 Korean sentences that explain what the figure shows, what the reader should focus on, and why it matters
  - for each major extracted table, include a Markdown table in the final report rather than only prose references
  - for each major metric, explain what it measures, how to read it, and whether higher or lower is better when that matters
  - prefer detail and specificity over brevity when the source text supports it

## Step 5: Save final Markdown

Write the final report to:
- `<summary_dir>/YYYYMMDD_<slugified_title>.md`
- If a PDF was fetched, call `python scripts/save_summary.py "<title>" "<temp_markdown_path>" "<pdf_path>"` so extracted figures are saved under `<summary_dir>/<slugified_title>/`, extracted tables are rendered as Markdown tables, automatic tags are inserted near the metadata block, and section 8 serves as a compact figure/table index.

Use this section structure:

# <Paper title>

- Original title:
- Input:
- Canonical URL:
- Source URLs:
- Date generated:
- Full text availability:

## 1. One-paragraph summary
## 2. Basic paper information
## 3. Problem definition
## 4. Core idea
## 5. Method details
### 5.1 Overall pipeline
### 5.2 Main modules
### 5.3 Training / inference details
## 6. Experimental setup
### 6.1 Datasets and evaluation targets
### 6.2 Metrics
### 6.3 Baselines
## 7. Main results
## 8. Figure / table notes
## 9. Strengths
## 10. Limitations
## 11. Critical commentary
## 12. Follow-up research ideas
## 13. Confidence and limitations of this summary

Minimum expectations for section depth:

- `6.1 Datasets and evaluation targets` must state what is evaluated, the prediction unit, the dataset split or scenario, and any special setting such as zero-shot / few-shot / cross-dataset evaluation.
- `6.2 Metrics` must define the reported metrics, not just name them.
- `6.2 Metrics` must explain how to interpret the metric values, including whether higher or lower is better and any thresholds / averaging choices that matter.
- `6.3 Baselines` must describe what each baseline changes relative to the proposed method.
- `7. Main results` must include the main quantitative comparisons, not only verbal conclusions.
- `8. Figure / table notes` must cover each major figure/table in the main paper, and relevant appendix items when they materially affect interpretation.
- `8. Figure / table notes` must explain figures and tables in Korean. Do not copy the raw English caption as the main figure description.
- Major tables in the main paper should appear as actual Markdown tables in the report, not only as prose descriptions.
- When extracted figures are available, place each figure image and its explanation near the most relevant section whenever possible. Use section `8. Figure / table notes` as a concise placement/index summary plus table-focused notes, not as a single gallery dump unless no better placement is possible.
- When extracted tables are available, place them near the most relevant results section whenever possible, and use section `8. Figure / table notes` as a concise placement/index summary rather than the only location where tables appear.
- `13. Confidence and limitations of this summary` must state what was directly observed versus inferred, and mention if any comparison numbers came from cited prior work rather than a reproduced run in the paper.

Recommended structure inside the report:

- In `6.1`, explicitly cover `evaluation target`, `prediction unit`, `dataset / split`, and `task setting`.
- In `6.2`, for each important metric, explain `definition`, `interpretation`, and `comparison caveats` when needed.
- In `8`, use entries such as `` `Fig. 1` `` or `` `Table 1` `` followed by Korean explanations that describe what is shown, how to read it, and the main takeaway.

# Trigger hints

Use this skill automatically when requests include phrases such as:
- summarize this paper
- review this paper
- explain this paper
- compare these papers
- organize these papers into markdown
- read this arXiv paper
- paper title: ...
- DOI: ...

# Important

If the user provides no detailed prompt beyond the paper input, still run the full workflow and produce the Markdown file automatically.
