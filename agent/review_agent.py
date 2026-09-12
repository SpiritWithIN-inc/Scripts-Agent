"""
review_agent.py — High-capability repository review agent.

Runs an LLM-powered deep review across target files and reports findings across:
- correctness and logic risks
- security and safety concerns
- reliability and edge cases
- maintainability and architecture
- performance opportunities
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from openai import OpenAI

    _OPENAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    _OPENAI_AVAILABLE = False

from scripts.common.file_ops import safe_read
from scripts.common.logger import get_logger

log = get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REVIEW_PATHS = (
    REPO_ROOT / "agent",
    REPO_ROOT / "scripts",
    REPO_ROOT / "main.py",
    REPO_ROOT / "README.md",
)

MAX_FILE_CHARS = 12000
MAX_CONTEXT_CHARS = 60000

REVIEW_SYSTEM_PROMPT = """\
You are an elite software review agent with maximum capabilities.

Perform a rigorous, production-grade review with advanced systems thinking.
Analyze:
1) correctness and logic defects
2) security vulnerabilities and misuse risks
3) reliability, failure modes, and edge cases
4) architecture and maintainability
5) performance bottlenecks and scalability risks
6) testability and observability gaps

Output requirements:
- Return concise markdown with these sections in order:
  1. Executive Summary
  2. Critical Findings
  3. Security Findings
  4. Reliability & Performance Findings
  5. Architecture & Maintainability Findings
  6. Recommended Action Plan
- For each finding include: severity (critical/high/medium/low), location, issue,
  why it matters, and concrete fix direction.
- If no finding exists in a section, explicitly state "No material findings."
"""


def _call_llm(messages: list[dict[str, str]], model: str = "gpt-4o") -> str:
    if not _OPENAI_AVAILABLE:
        raise RuntimeError("openai package is not installed. Run: pip install openai")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.1,
    )
    return response.choices[0].message.content or ""


class ReviewAgent:
    """Runs high-capability repository and file-level reviews."""

    def __init__(self, *, model: str = "gpt-4o") -> None:
        self.model = model
        log.info("ReviewAgent initialized (model=%s)", self.model)

    def review(self, request: str, *, targets: list[str] | None = None) -> str:
        files = self._resolve_targets(targets)
        context = self._build_context(files)
        messages = [
            {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Review request:\n{request.strip() or 'Perform a full system review.'}\n\n"
                    f"Repository context:\n{context}"
                ),
            },
        ]
        return _call_llm(messages, model=self.model).strip()

    def _resolve_targets(self, targets: list[str] | None) -> list[Path]:
        if not targets:
            resolved = []
            for entry in DEFAULT_REVIEW_PATHS:
                if entry.exists():
                    if entry.is_file():
                        resolved.append(entry)
                    else:
                        resolved.extend(
                            p for p in sorted(entry.rglob("*.py")) if p.is_file()
                        )
            return resolved

        resolved: list[Path] = []
        for target in targets:
            path = Path(target)
            if not path.is_absolute():
                path = REPO_ROOT / path
            path = path.resolve()
            if not path.exists():
                log.warning("Review target does not exist: %s", path)
                continue
            if path.is_file():
                resolved.append(path)
            else:
                resolved.extend(p for p in sorted(path.rglob("*.py")) if p.is_file())
        return resolved

    def _build_context(self, files: list[Path]) -> str:
        chunks: list[str] = []
        total = 0
        for file in files:
            try:
                rel = file.relative_to(REPO_ROOT)
            except ValueError:
                rel = file
            content = safe_read(file)
            if len(content) > MAX_FILE_CHARS:
                content = content[:MAX_FILE_CHARS] + "\n... [truncated]\n"
            section = f"\n### FILE: {rel}\n```python\n{content}\n```\n"
            projected = total + len(section)
            if projected > MAX_CONTEXT_CHARS:
                chunks.append("\n[Context truncated due to size limits.]\n")
                break
            chunks.append(section)
            total = projected

        if not chunks:
            return "No readable files were provided for review."
        return "".join(chunks)
