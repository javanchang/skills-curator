"""Regression tests for the hook: log-skill-usage.py.

Each test isolates the log file via the SKILL_USAGE_LOG env var (the hook
respects this), so tests don't touch the user's real `~/.claude/skill-usage.log`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "log-skill-usage.py"
PYTHON = sys.executable


def run_hook(payload: dict, log_path: Path) -> tuple[str, str, int]:
    """Invoke the hook with the given payload. Return (stdout, stderr, rc).

    The hook reads JSON from stdin and appends to SKILL_USAGE_LOG. We set
    SKILL_USAGE_LOG to a per-test path so tests are isolated.
    """
    env = os.environ.copy()
    env["SKILL_USAGE_LOG"] = str(log_path)
    env.setdefault("PYTHONIOENCODING", "utf-8")

    result = subprocess.run(
        [PYTHON, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    return result.stdout, result.stderr, result.returncode


def read_log(log_path: Path) -> list[list[str]]:
    if not log_path.exists():
        return []
    return [ln.rstrip("\n").split("\t") for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]


# ---------------------------------------------------------------------------
# Skill tool calls
# ---------------------------------------------------------------------------


def test_skill_tool_call_writes_user_kind(tmp_path):
    log = tmp_path / "skill.log"
    run_hook(
        {"tool_name": "Skill", "tool_input": {"skill": "code-review"}, "session_id": "s1"},
        log,
    )
    rows = read_log(log)
    assert len(rows) == 1
    assert rows[0] == [
        rows[0][0],   # ISO timestamp
        "s1",
        "skill",
        "user",
        "code-review",
    ]


def test_skill_tool_call_with_plugin_prefix_writes_plugin_kind(tmp_path):
    log = tmp_path / "skill.log"
    run_hook(
        {"tool_name": "Skill", "tool_input": {"skill": "superpowers:brainstorming"}, "session_id": "s1"},
        log,
    )
    rows = read_log(log)
    assert rows[0][3] == "plugin"
    assert rows[0][4] == "brainstorming"


def test_skill_tool_call_with_empty_skill_writes_nothing(tmp_path):
    log = tmp_path / "skill.log"
    run_hook({"tool_name": "Skill", "tool_input": {"skill": "  "}, "session_id": "s1"}, log)
    assert read_log(log) == []


def test_skill_tool_call_without_skill_arg_writes_nothing(tmp_path):
    log = tmp_path / "skill.log"
    run_hook({"tool_name": "Skill", "tool_input": {}, "session_id": "s1"}, log)
    assert read_log(log) == []


# ---------------------------------------------------------------------------
# Read tool — SKILL.md detection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path, expected_kind, expected_skill",
    [
        ("/home/u/.claude/skills/foo/SKILL.md",          "user",   "foo"),
        ("C:\\Users\\u\\.claude\\skills\\bar\\SKILL.md",  "user",   "bar"),
        ("/home/u/.claude/skills/baz/skill.md",          "user",   "baz"),  # case-insensitive
        ("/home/u/.claude/plugins/cache/m/superpowers/6.3.0/skills/brainstorming/SKILL.md",
                                                          "plugin", "brainstorming"),
        ("/home/u/.claude/plugins/marketplaces/x/y/plugins/code-review/skills/code-review/SKILL.md",
                                                          "plugin", "code-review"),
    ],
)
def test_read_skill_md_extracts_kind_and_name(tmp_path, path, expected_kind, expected_skill):
    log = tmp_path / "skill.log"
    run_hook(
        {"tool_name": "Read", "tool_input": {"file_path": path}, "session_id": "s1"},
        log,
    )
    rows = read_log(log)
    assert len(rows) == 1
    assert rows[0][2] == "read"
    assert rows[0][3] == expected_kind
    assert rows[0][4] == expected_skill


def test_read_non_skill_md_writes_nothing(tmp_path):
    log = tmp_path / "skill.log"
    run_hook(
        {"tool_name": "Read", "tool_input": {"file_path": "/home/u/.claude/CLAUDE.md"}, "session_id": "s1"},
        log,
    )
    assert read_log(log) == []


def test_read_outside_claude_dir_writes_nothing(tmp_path):
    log = tmp_path / "skill.log"
    run_hook(
        {"tool_name": "Read", "tool_input": {"file_path": "/tmp/SKILL.md"}, "session_id": "s1"},
        log,
    )
    assert read_log(log) == []


# ---------------------------------------------------------------------------
# Bash tool — npx skills matcher
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cmd, expected_skill",
    [
        ("npx skills code-review",       "code-review"),
        ("  npx   skills   foo ",        "foo"),
        ("yarn && npx skills my-plugin", "my-plugin"),
    ],
)
def test_bash_npx_skills(tmp_path, cmd, expected_skill):
    log = tmp_path / "skill.log"
    run_hook(
        {"tool_name": "Bash", "tool_input": {"command": cmd}, "session_id": "s1"},
        log,
    )
    rows = read_log(log)
    assert len(rows) == 1
    assert rows[0][2] == "bash"
    assert rows[0][3] == "plugin"
    assert rows[0][4] == expected_skill


def test_bash_without_npx_skills_writes_nothing(tmp_path):
    log = tmp_path / "skill.log"
    run_hook(
        {"tool_name": "Bash", "tool_input": {"command": "ls -la /tmp"}, "session_id": "s1"},
        log,
    )
    assert read_log(log) == []


# ---------------------------------------------------------------------------
# Other tools — must not write anything
# ---------------------------------------------------------------------------


def test_unknown_tool_writes_nothing(tmp_path):
    log = tmp_path / "skill.log"
    run_hook(
        {"tool_name": "Edit", "tool_input": {"file_path": "/home/u/.claude/skills/foo/SKILL.md"}, "session_id": "s1"},
        log,
    )
    assert read_log(log) == []


# ---------------------------------------------------------------------------
# Debounce
# ---------------------------------------------------------------------------


def test_debounce_collapses_repeated_events(tmp_path):
    log = tmp_path / "skill.log"
    payload = {"tool_name": "Skill", "tool_input": {"skill": "x"}, "session_id": "s1"}
    for _ in range(5):
        run_hook(payload, log)
    rows = read_log(log)
    # All 5 events within DEBOUNCE_SECONDS → only first one writes
    assert len(rows) == 1
    assert rows[0][4] == "x"


def test_debounce_respects_session_boundary(tmp_path):
    """Same skill, different sessions → both events are written."""
    log = tmp_path / "skill.log"
    run_hook(
        {"tool_name": "Skill", "tool_input": {"skill": "x"}, "session_id": "s1"},
        log,
    )
    run_hook(
        {"tool_name": "Skill", "tool_input": {"skill": "x"}, "session_id": "s2"},
        log,
    )
    rows = read_log(log)
    assert len(rows) == 2


def test_debounce_respects_kind_boundary(tmp_path):
    """Same skill, different kind (user vs plugin) → both written."""
    log = tmp_path / "skill.log"
    run_hook(
        {"tool_name": "Skill", "tool_input": {"skill": "x"}, "session_id": "s1"},
        log,
    )
    run_hook(
        {"tool_name": "Skill", "tool_input": {"skill": "superpowers:x"}, "session_id": "s1"},
        log,
    )
    rows = read_log(log)
    assert len(rows) == 2
    assert {r[3] for r in rows} == {"user", "plugin"}


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------


def test_malformed_json_does_not_crash(tmp_path):
    log = tmp_path / "skill.log"
    env = os.environ.copy()
    env["SKILL_USAGE_LOG"] = str(log)
    result = subprocess.run(
        [PYTHON, str(HOOK)],
        input="not json at all",
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    assert result.returncode == 0
    assert "cannot parse stdin" in result.stderr
    assert read_log(log) == []


def test_missing_tool_input_does_not_crash(tmp_path):
    log = tmp_path / "skill.log"
    run_hook({"tool_name": "Skill"}, log)
    assert read_log(log) == []


def test_session_id_falls_back_to_unknown(tmp_path):
    log = tmp_path / "skill.log"
    run_hook(
        {"tool_name": "Skill", "tool_input": {"skill": "x"}},  # no session_id
        log,
    )
    rows = read_log(log)
    assert rows[0][1] == "unknown"
