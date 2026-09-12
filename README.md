![Auto Assign](https://github.com/GODWthIN7/Scripts-Agent/actions/workflows/auto-assign.yml/badge.svg)

![Proof HTML](https://github.com/GODWthIN7/Scripts-Agent/actions/workflows/proof-html.yml/badge.svg)

# Copilot Script Agent

Copilot Agent is a personal AI‑driven script factory that turns natural language requests into polished, production‑ready Python automation scripts. It generates, organizes, and refines tools for system automation, data processing, Web/API integration, and general utilities.

## Key Features

- **Structured Script Generation** — scripts are placed into a predictable layout under `/scripts`
- **Polished Templates** — every generated script includes `main()`, `argparse` with `--dry-run`, logging, error handling, and a module docstring
- **Progress Bars** — `tqdm` integration for loops and batch operations
- **Proactive Assistance** — the agent suggests reusable helpers, refactors, and companion scripts
- **Safe Defaults** — dry-run mode by default; all writes scoped to `/scripts`
- **Extensible Agent Loop** — modular Python orchestration with LLM-backed planning

## Project Structure

```
/agent
    agent/coding_agent.py        # core agent loop and tool wrappers
/scripts
    /system_automation           # OS-level tasks, log archiving, file management
    /data_processing             # CSV/JSON ETL, reporting, normalization
    /web_api                     # HTTP clients, API pagination, web scraping
    /utilities                   # CLI helpers, format converters, general tools
    /common                      # shared helpers: logging, safe file ops, config
main.py                          # entrypoint to run the agent
requirements.txt
```

## Quick Start

```bash
git clone <repo-url>
cd Scripts-Agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
```

### List existing scripts

```bash
python main.py --list-files
python main.py --list-files --list-limit 100
```

### Get a plan (no files written)

```bash
python main.py --suggest "Create a script that fetches GitHub issues and exports them to CSV"
```

### Dry-run generation

```bash
python main.py "Archive logs older than 30 days and upload them to a backup folder"
```

### Write scripts to disk

```bash
python main.py --auto-apply "Archive logs older than 30 days and upload them to a backup folder"
```

## Example Tasks

| Category | Example |
|---|---|
| System automation | `Archive logs older than 30 days and upload them to a backup folder` |
| Data processing | `Merge multiple CSVs, normalize headers, and output a summary report` |
| Web/API | `Paginate through an API, respect rate limits, and store results as JSON` |
| Utilities | `Convert Markdown files to plain text and show progress` |

## Shared Helpers (`/scripts/common`)

| Module | Purpose |
|---|---|
| `logger.py` | Consistent logging setup via `get_logger(__name__)` |
| `file_ops.py` | `safe_write` / `safe_read` with dry-run support |
| `config.py` | `load_config()` and `require_env()` for env-var secrets |

## Safety and Best Practices

- **Dry-run by default** — pass `--auto-apply` to write files
- **Git snapshot recommended** before any write: `git add -A && git commit -m 'snapshot'`
- **Scope limits** — the agent writes only to `/scripts`
- **Secrets management** — store API keys in env vars; never commit them
- **Review generated code** — treat outputs as first drafts; review and test before use

## Contributing

1. Fork the repo and create a feature branch (`feature/<name>`)
2. Implement changes and add tests
3. Open a pull request with a clear description and examples
4. Keep feature branches short-lived and focused

## License

MIT
