# Log format

`log-skill-usage.py` writes one row per skill activation to
`~/.claude/skill-usage.log` (or whatever path `SKILL_USAGE_LOG` points at).

The format is **tab-separated**, with 5 columns:

| # | Column        | Example                          | Notes                                                        |
|---|---------------|----------------------------------|--------------------------------------------------------------|
| 0 | timestamp     | `2026-09-03T14:23:11.123456+00:00` | ISO-8601, UTC                                                |
| 1 | session id    | `s_abc123`                       | Falls back to `unknown` if the hook payload omits it         |
| 2 | source tool   | `skill` / `read` / `bash`        | Which PostToolUse matcher produced this event                |
| 3 | kind          | `user` / `plugin`                | `user` = under `~/.claude/skills/`, `plugin` = under `~/.claude/plugins/` |
| 4 | skill name    | `code-review`                    | Last segment of the skill's path, or plugin-prefixed name stripped |

Example row:

```
2026-09-03T14:23:11.123456+00:00	s_abc	skill	user	code-review
```

## Debounce

Repeated events for the same `(session_id, kind, skill)` triple within
`DEBOUNCE_SECONDS` (default 5s) are collapsed. This prevents the same
skill being recorded 2-3 times in a row when:

- Claude Code auto-loads a skill (Read of `SKILL.md`) **and** the user
  then calls `/skill` explicitly (Skill tool) within seconds
- The skill itself invokes `npx skills` (Bash) shortly after activation

## Reading the log in scripts

Always read the **last** column. Older versions of the hook used 2 or 3
columns; current is 5. The format is documented here for clarity, but the
audit script auto-detects by reading `cols[-1]`.

```python
from collections import Counter
counts = Counter(line.split("\t")[-1] for line in open(log) if "\t" in line)
```

## Why plain text / TSV and not JSON?

- Append-only: rows are written line-by-line, no read-modify-write
- Crash-safe: a partial final row can't corrupt the rest of the file
- Greppable: `grep code-review ~/.claude/skill-usage.log` works
- Tooling-free: anything that reads text can audit it

If you need structured access, convert with:

```bash
awk -F'\t' 'BEGIN{print "ts,session,source,kind,skill"} {print}' \
  ~/.claude/skill-usage.log > skill-usage.csv
```
