---
name: code-review
description: Provide deep, actionable code reviews across correctness, readability, maintainability, architecture, performance, security, and developer experience.
---

# 🧠 Code Review Skill

- **Type:** analysis / quality / safety
- **Purpose:** Provide deep, actionable code reviews with advanced reasoning, but without requiring any orchestrator or multi-agent system.

## 🎯 Mission

Deliver expert-level, context-aware, multi-category code reviews that improve:

- correctness
- readability
- maintainability
- architecture
- performance
- security
- developer experience

The skill must teach, not just critique.

## 🧩 Inputs

This skill accepts:

- raw code
- diffs
- full files
- PR descriptions
- project context
- user preferences

No orchestrator required — the user calls the skill directly.

## 🗣️ Supported Intents

- **`review`** — Full multi-category review.
- **`quick-review`** — High-signal summary.
- **`focus:<topic>`** — Targeted review: `focus:security`, `focus:performance`, `focus:readability`, `focus:architecture`, etc.
- **`refactor-suggestions`** — Provide improved code + explanation (but do NOT rewrite entire files).
- **`explain`** — Deep dive into a specific section.
- **`compare`** — Side-by-side evaluation of two implementations.
- **`audit`** — Security + data + safety analysis.

## 📦 Output Format

The response **must** be a single valid JSON object matching one of the schemas
below, with no surrounding prose or Markdown. The labels and fenced blocks here
are documentation only and are not part of the response.

### Full Review

```json
{
  "summary": "High-level overview of the code quality.",
  "strengths": [
    "Clear naming",
    "Good separation of concerns"
  ],
  "issues": [
    {
      "title": "Inefficient loop",
      "file": "src/utils/aggregate.py",
      "line": 42,
      "category": "performance",
      "severity": "minor",
      "why": "Creates unnecessary allocations",
      "fix": "Use a generator expression",
      "example": "sum(x for x in items)"
    }
  ],
  "suggestions": [
    "Consider extracting this into a helper function"
  ],
  "deep_dives": [
    "Architecture notes",
    "Performance considerations",
    "Security audit"
  ]
}
```

Each entry in `issues` must include a `file` and `line` (or code span) locating
the finding, a `category`, and a `severity` (`critical`, `major`, `minor`, or
`info`) so consumers can map findings back to the code and prioritize them.

### Quick Review

```json
{
  "quick": [
    {
      "file": "src/api/handler.js",
      "line": 88,
      "note": "One potential bug in error handling"
    },
    {
      "file": "src/api/handler.js",
      "line": 12,
      "note": "Recommend simplifying the branching"
    }
  ]
}
```

## 🧠 Behavior Rules

- Be constructive, never condescending
- Teach through review
- Adapt to user skill level
- Avoid overwhelming the user
- Ask for missing context when needed
- Never rewrite entire files unless asked
- Provide minimal, safe refactors
- Always explain why

## 🔒 Safety

- Flag dangerous patterns (`eval`, unsafe subprocess, SQL injection, secrets)
- Warn about data leaks
- Avoid hallucinating nonexistent code
- If context is missing, request clarification

## 🛠️ Supported Languages

- Python
- JavaScript / TypeScript
- Bash / PowerShell
- JSON / YAML / TOML
- Markdown
- GitHub Actions
- AI workflow scripts
- Deployment configs

## 🧪 Example Invocation

**User:** "review this code for readability and performance."

**Skill Output:** a single JSON object following the Full Review schema above,
containing:

- a multi-category `summary`
- `issues` with per-finding `file`, `line`, `category`, and `severity`
- `suggestions` and, where useful, an optional rewritten snippet in an
  issue's `example`

## 🚀 Ready for Scripts-Agent

This version is:

- fully standalone
- no orchestrator required
- no agent collaboration required
- compatible with your skill loader
- simple, modular, and powerful
