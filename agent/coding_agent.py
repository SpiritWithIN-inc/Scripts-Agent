"""
coding_agent.py — Core agent loop and tool wrappers for the Copilot Script Agent.

The agent accepts a natural-language task, plans which script(s) to create or
update, and then writes polished, production-ready Python automation scripts into
the /scripts directory tree.

Supported script categories
----------------------------
- system_automation   — file management, log archiving, OS-level tasks
- data_processing     — CSV/JSON manipulation, ETL, reporting
- web_api             — HTTP clients, API pagination, web scraping
- utilities           — CLI helpers, format converters, general tools

Safe defaults
-------------
- Dry-run mode is on by default; pass ``--auto-apply`` to write files.
- All writes are confined to the /scripts directory.
- Recommends a git snapshot before any write operation.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    _OPENAI_AVAILABLE = False

from scripts.common.logger import get_logger
from scripts.common.file_ops import safe_write, safe_read

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_ROOT = REPO_ROOT / "scripts"

CATEGORIES = {
    "system_automation": SCRIPTS_ROOT / "system_automation",
    "data_processing": SCRIPTS_ROOT / "data_processing",
    "web_api": SCRIPTS_ROOT / "web_api",
    "utilities": SCRIPTS_ROOT / "utilities",
}

SCRIPT_TEMPLATE = '''\
"""
{docstring}
"""

from __future__ import annotations

import argparse
import logging
import sys

from scripts.common.logger import get_logger

log = get_logger(__name__)


def main(args: argparse.Namespace) -> int:
    """Entry point for {name}."""
    log.info("Starting %s (dry_run=%s)", __file__, args.dry_run)

    # TODO: implement task logic here

    log.info("Done.")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="{description}")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would be done without making changes.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main(parse_args()))
'''

SYSTEM_PROMPT = """\
You are Copilot Script Agent — an expert Python automation engineer.

Your job:
1. Analyze the user task.
2. Decide which category (system_automation, data_processing, web_api, utilities) each
   script belongs to.  A task may require more than one script.
3. For each script produce a JSON plan entry:
   {
     "category": "<category>",
     "filename": "<snake_case_name>.py",
     "description": "<one-line description>",
     "docstring": "<module docstring paragraph>",
     "body": "<complete Python source code as a string>"
   }
4. Return ONLY a JSON array of plan entries and nothing else.

Script rules:
- Always include main(), argparse with --dry-run, logging, and a top-of-file docstring.
- Use tqdm for any loop/batch operation with a sensible desc= and unit=.
- Import shared helpers from scripts.common (logger, file_ops, config) when relevant.
- Never import or use secrets directly — read from env vars.
- All file writes go through scripts.common.file_ops.safe_write unless there is a
  compelling reason (document it).
"""


# ---------------------------------------------------------------------------
# Tool helpers
# ---------------------------------------------------------------------------

def _log_perf(stage: str, started_at: float, *, level: int = logging.INFO, **fields: Any) -> None:
    """Emit a concise perf log line for *stage*."""
    elapsed_ms = (time.perf_counter() - started_at) * 1000
    metrics = " ".join(f"{k}={v}" for k, v in fields.items())
    log.log(level, "perf.%s elapsed_ms=%.2f %s", stage, elapsed_ms, metrics)


def tool_list_files(
    directory: str | Path = SCRIPTS_ROOT,
    *,
    limit: int | None = None,
) -> list[str]:
    """Return a sorted list of files under *directory* relative to REPO_ROOT."""
    started_at = time.perf_counter()
    base = Path(directory)
    if not base.exists():
        _log_perf("tool_list_files", started_at, files=0, limit=limit)
        return []

    files: list[str] = []
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        files.append(str(path.relative_to(REPO_ROOT)))

    files.sort()
    if limit is not None:
        files = files[:limit]
    _log_perf("tool_list_files", started_at, files=len(files), limit=limit)
    return files


def tool_read_file(path: str | Path) -> str:
    """Return the text content of *path* (resolved relative to REPO_ROOT if needed)."""
    resolved = _resolve_path(path)
    return safe_read(resolved)


def tool_write_file(path: str | Path, content: str, *, dry_run: bool = True) -> str:
    """Write *content* to *path* and return a status message."""
    resolved = _resolve_path(path)
    _assert_in_scripts(resolved)
    return safe_write(resolved, content, dry_run=dry_run)


def tool_run_command(cmd: list[str], *, cwd: str | Path = REPO_ROOT) -> str:
    """Run *cmd* in a subprocess and return combined stdout+stderr."""
    log.debug("Running command: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=120,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        log.warning("Command exited with code %d", result.returncode)
    return output.strip()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_path(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = REPO_ROOT / p
    return p.resolve()


def _assert_in_scripts(path: Path) -> None:
    """Raise ValueError if *path* is outside the /scripts directory."""
    try:
        path.relative_to(SCRIPTS_ROOT.resolve())
    except ValueError:
        raise ValueError(
            f"Safety violation: attempted write to '{path}' which is outside "
            f"the allowed /scripts directory."
        )


def _parse_plan(raw: str) -> list[dict[str, Any]]:
    """Extract and parse the JSON plan from *raw* LLM output."""
    raw = raw.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(
            line for line in lines if not line.startswith("```")
        )
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

class CodingAgent:
    """Orchestrates the LLM-driven script generation loop."""

    def __init__(
        self,
        *,
        dry_run: bool = True,
        auto_apply: bool = False,
        model: str = "gpt-4o-mini",
    ) -> None:
        self.dry_run = dry_run and not auto_apply
        self.model = model
        self._client: Any | None = None
        log.info(
            "CodingAgent initialized (dry_run=%s, model=%s)",
            self.dry_run,
            self.model,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, task: str) -> list[Path]:
        """Run the agent for *task* and return the list of files written."""
        log.info("Task: %s", task)

        if not self.dry_run:
            self._recommend_git_snapshot()

        plan = self._plan(task)
        log.info("Plan contains %d script(s).", len(plan))

        written: list[Path] = []
        apply_started_at = time.perf_counter()
        for entry in plan:
            path = self._apply_entry(entry)
            if path:
                written.append(path)
        _log_perf("apply_entry_total", apply_started_at, entries=len(plan), written=len(written))

        return written

    def suggest(self, task: str) -> str:
        """Return a human-readable plan without writing any files."""
        plan = self._plan(task)
        lines = ["Suggested plan:"]
        for i, entry in enumerate(plan, 1):
            cat = entry.get("category", "?")
            fn = entry.get("filename", "?")
            desc = entry.get("description", "")
            lines.append(f"  {i}. [{cat}] {fn} — {desc}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _plan(self, task: str) -> list[dict[str, Any]]:
        started_at = time.perf_counter()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ]
        raw = self._call_llm(messages, model=self.model)
        plan = _parse_plan(raw)
        _log_perf("plan", started_at, entries=len(plan))
        return plan

    def _apply_entry(self, entry: dict[str, Any]) -> Path | None:
        started_at = time.perf_counter()
        category = entry.get("category", "utilities")
        filename = entry.get("filename", "script.py")
        body = entry.get("body", "")

        if category not in CATEGORIES:
            log.warning("Unknown category '%s'; defaulting to utilities.", category)
            category = "utilities"

        dest = CATEGORIES[category] / filename
        result = tool_write_file(dest, body, dry_run=self.dry_run)
        log.info(result)
        _log_perf(
            "apply_entry",
            started_at,
            level=logging.DEBUG,
            category=category,
            filename=filename,
            dry_run=self.dry_run,
        )
        return None if self.dry_run else dest

    def _get_client(self) -> Any:
        """Return an OpenAI client, lazily initialized and reused per instance."""
        if self._client is not None:
            return self._client
        if not _OPENAI_AVAILABLE:
            raise RuntimeError("openai package is not installed. Run: pip install openai")
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
        self._client = OpenAI(api_key=api_key)
        return self._client

    def _call_llm(self, messages: list[dict[str, str]], model: str) -> str:
        """Call the OpenAI chat API and return the assistant message content."""
        started_at = time.perf_counter()
        client = self._get_client()
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
        )
        content = response.choices[0].message.content
        _log_perf("call_llm", started_at, model=model, messages=len(messages))
        return content

    def _recommend_git_snapshot(self) -> None:
        log.info(
            "Recommendation: create a git snapshot before the agent writes files.\n"
            "  git add -A && git commit -m 'snapshot before agent run'"
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Copilot Script Agent — generates Python automation scripts.",
    )
    parser.add_argument("task", nargs="?", help="Natural-language task description.")
    parser.add_argument(
        "--auto-apply",
        action="store_true",
        default=False,
        help="Write generated scripts to disk (default: dry-run only).",
    )
    parser.add_argument(
        "--suggest",
        action="store_true",
        default=False,
        help="Print a plan without writing any files.",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="OpenAI model to use (default: gpt-4o-mini).",
    )
    parser.add_argument(
        "--list-files",
        action="store_true",
        default=False,
        help="List existing scripts and exit.",
    )
    parser.add_argument(
        "--list-limit",
        type=int,
        default=None,
        help="Optional max number of files returned by --list-files.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_files:
        files = tool_list_files(limit=args.list_limit)
        if files:
            print("\n".join(files))
        else:
            print("No scripts found.")
        return 0

    if not args.task:
        parser.print_help()
        return 1

    agent = CodingAgent(
        dry_run=not args.auto_apply,
        auto_apply=args.auto_apply,
        model=args.model,
    )

    if args.suggest:
        print(agent.suggest(args.task))
        return 0

    written = agent.run(args.task)
    if written:
        print("Files written:")
        for p in written:
            print(f"  {p.relative_to(REPO_ROOT)}")
    else:
        print("Dry-run complete — no files written. Pass --auto-apply to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
