"""Regression tests for the auto-detection logic in the SKILL.md audit spec.

The original spec used a hard-coded `awk '{print $2}'`, which read the wrong
column after the log format grew from 2 to 5 columns. The fix is to read the
*last* column (skill name) regardless of format. These tests pin that
contract so future format changes can't silently break counting.

Each fixture in tests/fixtures/ represents a different historical log
shape. The format-detection logic must produce sensible counts for all of
them.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def detect_last_column(log_path: Path) -> list[str]:
    """Return the skill column for every line in `log_path`.

    Mirrors the logic in the SKILL.md spec: take the last column of each
    tab-separated row, skipping blank / non-tab lines.
    """
    if not log_path.exists():
        return []
    skills = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or "\t" not in line:
            continue
        cols = line.split("\t")
        skills.append(cols[-1])
    return skills


def count_skills(log_path: Path) -> Counter:
    return Counter(detect_last_column(log_path))


# ---------------------------------------------------------------------------
# Each format should yield sensible counts (the audit report doesn't care
# which column is which — only the *last* one is always the skill name).
# ---------------------------------------------------------------------------


def test_2col_format_counts():
    counts = count_skills(FIXTURES / "2col.log")
    assert counts == {"code-review": 1, "skills-curator": 1, "brainstorming": 1}


def test_3col_format_counts():
    counts = count_skills(FIXTURES / "3col.log")
    assert counts == {"code-review": 1, "skills-curator": 1, "brainstorming": 1}


def test_4col_format_counts():
    counts = count_skills(FIXTURES / "4col.log")
    assert counts == {"code-review": 1, "skills-curator": 1, "brainstorming": 1}


def test_5col_format_counts():
    counts = count_skills(FIXTURES / "5col.log")
    assert counts == {
        "code-review": 1,
        "skills-curator": 2,   # used twice in different sessions
        "brainstorming": 1,
        "test-skill": 1,
    }


def test_empty_log_counts_to_nothing():
    assert count_skills(FIXTURES / "empty.log") == Counter()


def test_missing_log_returns_empty():
    assert count_skills(FIXTURES / "does-not-exist.log") == Counter()


def test_mixed_lines_skip_garbage():
    """Blank lines and lines without a tab must be skipped, not counted."""
    counts = count_skills(FIXTURES / "mixed.log")
    assert counts == {
        "code-review": 1,
        "skills-curator": 1,
        "brainstorming": 1,
        "test-skill": 1,
    }


# ---------------------------------------------------------------------------
# The bug that originally prompted the fix: a hard-coded `{print $2}` reads
# column 2, which is the session id in the 5-column format. The audit
# report's "调用次数" column must reflect skill *names*, not session ids.
# ---------------------------------------------------------------------------


def test_5col_format_does_not_count_session_id_as_skill():
    counts = count_skills(FIXTURES / "5col.log")
    # If we (wrongly) read column 2, we'd see "s1" / "s2" / "s3" — the
    # session ids — instead of skill names. The fixed logic never sees
    # them because we read the *last* column.
    assert "s1" not in counts
    assert "s2" not in counts
    assert "s3" not in counts
    assert all(s not in {"s1", "s2", "s3", "skill", "read", "bash", "user", "plugin"}
               for s in counts)
