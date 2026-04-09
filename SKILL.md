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
4. Save fetched source files in `~/Documents/paper-summary-agent/downloaded/`.
5. When a PDF source is available, extract embedded figures into `~/Documents/paper-summary-agent/summary/<slugified_title>/` and embed them in the final Markdown so the figures render directly in the report.
6. Use subagents explicitly for non-trivial paper tasks:
   - `resolver` for identity resolution and source gathering
   - `method-analyst` for architecture/method details
   - `experiment-analyst` for datasets, metrics, results, and limitations
   - `writer` for final Korean Markdown synthesis
7. Final output file must be a Korean Markdown file saved to `~/Documents/paper-summary-agent/summary/`.
8. Agent-facing instructions, filenames, code comments, and internal templates should remain in English unless Korean is necessary in the final report.
9. If full text cannot be obtained, still produce the summary and clearly mark `Full text unavailable` near the top.
10. Avoid unsupported claims. Distinguish observed facts from inference.
11. Keep long verbatim quotes to a minimum.
12. By default, use the latest available frontier model for paper-analysis subagents. Prefer `gpt-5.4` with `high` or `xhigh` reasoning effort for `method-analyst`, `experiment-analyst`, and `writer`, unless the user explicitly asks for a faster/cheaper option.
13. Default to a thorough report rather than a brief summary. Do not stop at a high-level abstract-style overview when the full text is available.
14. The experiment analysis must explicitly cover:
   - evaluation metrics and how they are defined
   - evaluation protocol and training/inference setup
   - main quantitative results
   - ablations, efficiency measurements, and limitations
   - figure-by-figure and table-by-table notes for the main paper, plus important appendix tables/figures when relevant
15. If the first analysis pass is missing metrics, protocol details, or important figure/table explanations, do a second pass before writing the final report.

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
  - identify datasets, metrics, metric definitions, evaluation protocol, baselines, main tables/figures, appendix evidence, ablations, efficiency, failure modes, and limitations
- `writer`
  - use the latest available frontier model, preferably `gpt-5.4`
  - synthesize the final Korean Markdown file using the required template
  - prefer detail and specificity over brevity when the source text supports it

## Step 5: Save final Markdown

Write the final report to:
- `~/Documents/paper-summary-agent/summary/YYYYMMDD_<slugified_title>.md`
- If a PDF was fetched, call `python scripts/save_summary.py "<title>" "<temp_markdown_path>" "<pdf_path>"` so extracted figures are saved under `~/Documents/paper-summary-agent/summary/<slugified_title>/` and embedded into the Markdown under section 8.

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
### 6.1 Datasets
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

- `6.2 Metrics` must define the reported metrics, not just name them.
- `6.3 Baselines` must describe what each baseline changes relative to the proposed method.
- `7. Main results` must include the main quantitative comparisons, not only verbal conclusions.
- `8. Figure / table notes` must cover each major figure/table in the main paper, and relevant appendix items when they materially affect interpretation.
- When extracted figures are available, section `8. Figure / table notes` should include rendered figure images before the written notes.
- `13. Confidence and limitations of this summary` must state what was directly observed versus inferred, and mention if any comparison numbers came from cited prior work rather than a reproduced run in the paper.

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
