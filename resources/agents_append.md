## Paper summary workflow

When the user provides a paper title, DOI, paper page URL, or PDF URL, automatically activate the `paper-summary-agent` skill.

Behavior requirements:
- Use live web search if identity resolution is uncertain.
- Explicitly spawn subagents for substantial paper-analysis tasks.
- Internal agent instructions stay in English.
- Save fetched source files under `~/Documents/paper-summary-agent/downloaded/`.
- Final saved report must be in Korean Markdown under `~/Documents/paper-summary-agent/summary/`.
- When a PDF is available, extract embedded figures into `~/Documents/paper-summary-agent/summary/<slugified_title>/` and embed them in the Markdown report.
- If full text is unavailable, say so clearly in the report.
- Do not wait for the user to provide an extra prompt if the paper input is already sufficient.
- Use the latest available frontier model for subagents by default, preferably `gpt-5.4`, and use `high` or `xhigh` reasoning effort for deep paper analysis unless the user asks for speed over depth.
- Default to a comprehensive report. Cover evaluation metrics, evaluation protocol, major figures/tables, and important appendix evidence when the source text is available.
