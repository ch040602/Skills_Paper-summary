## Paper summary workflow

When the user provides a paper title, DOI, paper page URL, or PDF URL, automatically activate the `paper-summary-agent` skill.

Behavior requirements:
- Use live web search if identity resolution is uncertain.
- Explicitly spawn subagents for substantial paper-analysis tasks.
- Internal agent instructions stay in English.
- Save fetched source files under the configured download directory from `scripts/paths.py` or `PAPER_SUMMARY_AGENT_DOWNLOAD_DIR`.
- Final saved report must be in Korean Markdown under the configured Obsidian summary directory from `scripts/paths.py` or `PAPER_SUMMARY_AGENT_SUMMARY_DIR`.
- When a PDF is available, extract embedded figures into `<summary_dir>/<slugified_title>/` and embed them in the Markdown report with relative links.
- If full text is unavailable, say so clearly in the report.
- Do not wait for the user to provide an extra prompt if the paper input is already sufficient.
- Use the latest available frontier model for subagents by default, preferably `gpt-5.4`, and use `high` or `xhigh` reasoning effort for deep paper analysis unless the user asks for speed over depth.
- Default to a comprehensive report. Cover evaluation targets, metric definitions, evaluation protocol, major figures/tables, and important appendix evidence when the source text is available.
- Figure descriptions in the final report must be Korean explanations of what the figure shows and why it matters, not raw English captions.
