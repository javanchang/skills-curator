#!/usr/bin/env python3
"""Claude Code PostToolUse hook: deduped log of every skill activation.

A "skill activation" is any of:

  1. ``Skill`` tool call                  → source=``skill``
  2. ``Read`` of any ``**/SKILL.md``       → source=``read``
       - matches under both ``~/.claude/skills/<name>/SKILL.md``
         AND ``~/.claude/plugins/.../skills/<name>/SKILL.md``
       - ``kind`` is ``user`` or ``plugin`` based on the path prefix
  3. ``Bash`` matching ``npx skills <name>`` → source=``bash``

Deduplication rules:

  - Same (session, kind, skill) within ``DEBOUNCE_SECONDS`` collapses to one row.
  - ``Skill`` tool internally Reads SKILL.md, but those two events fall inside
    the debounce window for the same (session, kind, skill) triple, so they
    count as ONE activation.
  - User skills and plugin skills with the same name are tracked separately
    (different ``kind``).
  - Different sessions are tracked separately.

Log format (tab-separated, one record per line)::

    <ISO-timestamp> <session-id> <source> <kind> <skill>

Customizing the log location:

  - Default: ``~/.claude/skill-usage.log``
  - Override with the ``SKILL_USAGE_LOG`` environment variable.

Never blocks Claude Code — all errors go to stderr with exit 0.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# --- Configuration ---------------------------------------------------------

# Log path: env override > default at ~/.claude/skill-usage.log
LOG = Path(os.environ.get("SKILL_USAGE_LOG", str(Path.home() / ".claude" / "skill-usage.log")))

# Match any SKILL.md (or skill.md, case-insensitive) ending the path.
# Capture group 1 = the directory immediately containing SKILL.md (= skill name).
SKILL_MD_NAME_RE = re.compile(r"[/\\]([^/\\]+)[/\\][Ss][Kk][Ii][Ll][Ll]\.md$")

# Path prefix discriminators.
USER_PREFIX = "/.claude/skills/"
PLUGIN_PREFIX = "/.claude/plugins/"

# Plugin entry: `npx skills <name>`
NPX_SKILLS_RE = re.compile(r"\bnpx\s+skills\s+(\S+)")

# Debounce: same (session, kind, skill) within this window → suppress
DEBOUNCE_SECONDS = 5

# How much of the log tail to scan when checking for recent duplicates
DEDUP_TAIL_BYTES = 4096


# --- Logging ----------------------------------------------------------------


def _recent_dup(session: str, kind: str, skill: str, now: "datetime") -> bool:
    """Return True if an identical record was written within DEBOUNCE_SECONDS.

    Reads only the tail of the log file to keep this cheap.
    """
    if not LOG.exists():
        return False
    try:
        with LOG.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - DEDUP_TAIL_BYTES))
            tail = f.read().decode("utf-8", errors="replace")
    except Exception:
        return False

    cutoff = now - timedelta(seconds=DEBOUNCE_SECONDS)
    for line in reversed(tail.splitlines()):
        parts = line.split("\t")
        # Only the v3+ (5-col) format carries session + kind. Earlier formats
        # can't be deduped safely — we conservatively let them through.
        if len(parts) < 5:
            continue
        try:
            ts = datetime.fromisoformat(parts[0])
        except ValueError:
            continue
        if ts < cutoff:
            return False
        if (
            parts[1] == session
            and parts[3] == kind
            and parts[4] == skill
        ):
            return True
    return False


def log_event(session: str, source: str, kind: str, skill: str) -> None:
    """Append one record to the log file, debounced."""
    skill = skill.strip()
    if not skill:
        return
    now = datetime.now()
    if _recent_dup(session, kind, skill, now):
        return
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(
                f"{now.isoformat(timespec='seconds')}\t{session}\t{source}\t{kind}\t{skill}\n"
            )
    except Exception as exc:
        sys.stderr.write(f"log-skill-usage: cannot write log: {exc}\n")


# --- Skill name extraction --------------------------------------------------


def skill_from_read(path: str):
    """Return ``(kind, skill_name)`` where kind ∈ {'user', 'plugin'}, or None."""
    norm = path.replace("\\", "/")
    m = SKILL_MD_NAME_RE.search(norm)
    if not m:
        return None
    name = m.group(1)
    if USER_PREFIX in norm:
        return "user", name
    if PLUGIN_PREFIX in norm:
        return "plugin", name
    return None


# --- Main -------------------------------------------------------------------


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception as exc:
        sys.stderr.write(f"log-skill-usage: cannot parse stdin: {exc}\n")
        return 0

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    session = payload.get("session_id", "unknown")

    if tool_name == "Skill":
        skill = (tool_input.get("skill") or "").strip()
        if skill:
            # A Skill call is ambiguous w.r.t. kind — use the basename heuristic:
            # bare name → assume "user"; "<plugin>:<name>" → "plugin".
            if ":" in skill:
                _, _, name = skill.partition(":")
                log_event(session, "skill", "plugin", name or skill)
            else:
                log_event(session, "skill", "user", skill)

    elif tool_name == "Read":
        path = tool_input.get("file_path", "")
        info = skill_from_read(path)
        if info:
            kind, skill = info
            log_event(session, "read", kind, skill)

    elif tool_name == "Bash":
        cmd = tool_input.get("command", "")
        m = NPX_SKILLS_RE.search(cmd)
        if m:
            log_event(session, "bash", "plugin", m.group(1))

    # Everything else: ignored.

    return 0


if __name__ == "__main__":
    sys.exit(main())
