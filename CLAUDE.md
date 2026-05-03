# CLAUDE.md — Academic Summarizer (UNO)

Project context for Claude Code. Read this before making changes.

## What this project does

Scrapes PDFs/DOCX from UNO's Moodle campus, summarizes them with AI (Groq or Anthropic), saves results to Notion or drive. Runs as CLI or TUI.

## Key commands

```cmd
python tui.py                          # Launch full TUI (recommended)
python main.py                         # Run full pipeline (download + summarize)
python main.py --dry-run               # Preview without API calls
python main.py --skip-download         # Summarize only (no campus scrape)
python main.py --download-only         # Download only (no AI)
python main.py --subject "Algebra"     # Filter by subject
python main.py --reset                 # Reprocess all files
```

## File structure

```
main.py          — orchestration, run() function, CLI entry point
tui.py           — Textual TUI app (6 panels: Estado/Proveedor/Modelo/Keys/Prompt/Ejecutar)
config.py        — all settings, loads from .env via python-dotenv
.env             — secrets (never commit)
.env.example     — template for .env
src/
  ai_client.py       — summarize_text(), estimate_cost(), Groq + Anthropic
  campus_downloader.py — Playwright Moodle scraper
  extractor.py       — PDF (pdfplumber) + DOCX text extraction
  notion_writer.py   — Notion API, pages.create + blocks.children.append
  tracker.py         — MD5-based processed file tracking
```

## Config and secrets

All secrets in `.env`. `config.py` reads via `os.environ.get()`. After editing `.env`, call `reload_config()` in `tui.py` (handles `importlib.reload` + `load_dotenv(override=True)`).

Key config vars:
- `PROVIDER` — `"groq"` (default, free) or `"anthropic"` (paid)
- `GROQ_MODEL` — default `llama-3.3-70b-versatile`
- `MODEL` — Anthropic model, default `claude-haiku-4-5-20251001`
- `DOCUMENTS_ROOT` — folder with PDFs/DOCX organized by subject subfolder
- `NOTION_DATABASE_ID` — 32-char ID from Notion URL

## AI providers

Groq free tier limits: 30 req/min, 6000 tok/min, 100k tok/day.
`estimate_cost(word_count)` returns `(usd_cost, pdfs_remaining_groq)`.
Anthropic: cost in USD, no daily limit.

Prompt template uses `{text}` placeholder — replaced with `.replace("{text}", text)`, NOT `.format()` (PDFs can contain curly braces).

## Moodle / campus scraper

Course name format: `01017-Álgebra y Geometría Analítica (1C2024)`. Year extracted via regex `r'\d[Cc](\d{2,4})'`. Moodle lists resources ascending — last = most recent. Uses Playwright headless Chromium.

## Notion writer

`pages.create()` max 100 children blocks. Overflow via `blocks.children.append()`. Each rich_text block max 2000 chars — `_make_blocks()` splits. Empty text returns `[]` (Notion rejects empty blocks).

## TUI architecture

`tui.py` — Textual app. Sidebar `ListView` + `ContentSwitcher`. Each panel is a `ScrollableContainer`. Save writes to `.env` via `dotenv.set_key()`. `reload_config()` reloads both `config` and `src.ai_client` modules. `main.run()` called via `asyncio.to_thread` — non-blocking. Log streamed via custom `logging.Handler` using `app.call_from_thread`.

## Dependencies

```
anthropic groq pdfplumber python-docx notion-client playwright python-dotenv textual
```

Install: `install.bat` or `pip install <above> && playwright install chromium`.

## Git

Default branch: `main`. Use `git branch --show-current` for the active branch.
