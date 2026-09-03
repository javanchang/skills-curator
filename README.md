# skills-curator

Curate installed Claude/Codex/agent skills: **disk usage · call frequency · keep/prune recommendations**.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-≥3.8-blue.svg)](pyproject.toml)
[![Claude Code](https://img.shields.io/badge/Claude_Code-skill-blueviolet)](https://docs.claude.com/claude-code)

---

## What it does

| Step | Question answered |
|---|---|
| 1. Disk usage | Which skills take the most disk? |
| 2. Call frequency | Which skills are actually used, and how often? |
| 3. 30-day unused | Which skills haven't been touched in a month? |
| 4. Verdict | Should I keep or uninstall each skill? |

Three call sources are tracked so plugin skills and auto-loaded skills count too:
- `Skill` tool calls (explicit invocation)
- `Read` of any `**/SKILL.md` (auto-loaded by the agent)
- `Bash` matching `npx skills <name>` (plugin entrypoint)

> **Not Claude-only.** The hook is intentionally narrow — it only logs `**/SKILL.md` reads under `~/.claude/skills/` and `~/.claude/plugins/`. Adding support for Codex / Antigravity / other agents is a matter of pointing `--skills-dir` and `--plugins-dir` at their directories; the verdict logic itself is agent-agnostic.

---

## Install

### Option 1: One-line install (recommended)

From any shell, after `git clone`-ing the repo:

```bash
# Linux / macOS
bash scripts/install-local.sh

# Windows PowerShell
.\scripts\install-local.ps1
```

The script is **idempotent** — re-running it updates files in place, no duplicates. It will:

1. Copy `SKILL.md` → `~/.claude/skills/curator/SKILL.md`
2. Copy `hooks/log-skill-usage.py` → `~/.claude/hooks/log-skill-usage.py`
3. Merge a `PostToolUse` entry into `~/.claude/settings.json` (matcher: `Skill|Read|Bash`)
4. Copy `bin/skills-curator` → `~/.local/bin/skills-curator` and print a PATH hint

After install, invoke the skill with `/curator` (the slash-command name comes from
`SKILL.md`'s frontmatter `name: curator`, not the repo name).

### Option 2: Install from GitHub via `npx skills`

Once the repo is published to GitHub, anyone can install the skill with:

```bash
npx skills add https://github.com/javanchang/skills-curator
```

**What this gets you:** the `SKILL.md` only — the skill description and the bash heredocs that read `~/.claude/skill-usage.log`.

**What this does NOT get you:** the hook. `npx skills add` doesn't ship executables. Without the hook, every report will say "hook 未启用". So after `npx skills add`, run the hook installer:

```bash
# Linux / macOS — pull just the hook file and install it
curl -fsSL https://raw.githubusercontent.com/javanchang/skills-curator/main/hooks/log-skill-usage.py \
  > ~/.claude/hooks/log-skill-usage.py
# then merge the matcher into settings.json (see Option 1, step 3)

# Windows PowerShell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/javanchang/skills-curator/main/hooks/log-skill-usage.py" `
  -OutFile "$env:USERPROFILE\.claude\hooks\log-skill-usage.py"
# then merge the matcher into settings.json
```

### Option 3: Manual copy (when nothing else works)

```bash
mkdir -p ~/.claude/skills/curator
cp SKILL.md ~/.claude/skills/curator/SKILL.md
mkdir -p ~/.claude/hooks
cp hooks/log-skill-usage.py ~/.claude/hooks/log-skill-usage.py
# Then merge `hooks.PostToolUse` into ~/.claude/settings.json manually.
```

---

## Verify it works

Restart Claude Code so the hook takes effect, then call any skill (e.g.
`/curator`) and check the log:

```bash
cat ~/.claude/skill-usage.log
```

You should see tab-separated rows like:

```
2026-09-03T09:28:20  sess-A  skill  user    code-review
2026-09-03T09:28:20  sess-A  read   plugin  brainstorming
```

If the file doesn't exist → re-check your `settings.json` and python path.

---

## Use

Just run `/curator` inside Claude Code. It will run the four-step report
and print actionable keep/uninstall recommendations.

The skill is fully self-contained — no Python deps, no network calls, no side
effects beyond reading `~/.claude/skill-usage.log` and `du`-ing your skills dir.

For scripted use (cron, CI, etc.), the standalone CLI does the same job:

```bash
bin/skills-curator --log ~/.claude/skill-usage.log \
                   --skills-dir ~/.claude/skills \
                   --plugins-dir ~/.claude/plugins
```

To audit a Codex install instead of (or in addition to) Claude:

```bash
bin/skills-curator --log ~/.codex/skill-usage.log \
                   --skills-dir ~/.codex/skills
```

---

## Repository layout

```
skills-curator/
├── README.md                ← this file
├── SKILL.md                 ← the skill itself (top-level for `npx skills add`)
├── LICENSE                  ← MIT
├── CHANGELOG.md             ← version history
├── CONTRIBUTING.md          ← how to contribute
├── SECURITY.md              ← vulnerability reporting
├── pyproject.toml           ← packaging metadata
├── pytest.ini
├── .gitignore
├── hooks/
│   ├── log-skill-usage.py   ← PostToolUse hook
│   └── README.md            ← hook details
├── bin/
│   └── skills-curator       ← standalone CLI (optional)
├── scripts/
│   ├── install-local.sh     ← one-shot install (Linux/macOS)
│   ├── install-local.ps1    ← one-shot install (Windows)
│   ├── install-hook.sh      ← hook-only install (legacy)
│   └── install-hook.ps1     ← hook-only install (legacy)
├── tests/
│   ├── test_hook.py
│   ├── test_format_detection.py
│   └── fixtures/
│       ├── 2col.log, 3col.log, 4col.log, 5col.log
│       ├── empty.log
│       └── mixed.log
└── docs/
    ├── log-format.md        ← spec of ~/.claude/skill-usage.log
    └── verdicts.md          ← how the keep/uninstall rules are derived
```

> **Layout note:** `SKILL.md` lives at the repo root, not under `skill/`.
> This is the canonical layout that `npx skills add` discovers — a repo
> with `SKILL.md` at the root is treated as a single-skill repo.
>
> **Naming note:** the repo is `skills-curator`, the Python package is
> `skills-curator`, the CLI is `skills-curator`, but the **slash-command
> inside Claude Code is `/curator`** (no `skills-` prefix — shorter to
> type). The mapping is set by the `name:` field in `SKILL.md` frontmatter.

---

## Verdict rules

| Condition | Verdict |
|---|---|
| Used ≥ 1×/week | Keep |
| > 1MB and unused for 30 days | Suggest uninstall |
| > 5MB and never used | Suggest uninstall |
| Rarely used but obviously saves time | Keep (ask user) |
| Never seen and > 100K | Suggest uninstall |

The rules are documented in `docs/verdicts.md` and intentionally conservative —
when in doubt, keep.

---

## Development

```bash
git clone https://github.com/javanchang/skills-curator
cd skills-curator
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
pytest
```

When you change the skill or hook and want to test locally without
re-publishing to GitHub:

```bash
bash scripts/install-local.sh    # or .\scripts\install-local.ps1
```

Then restart Claude Code and run `/curator`.

---

## Release flow

1. Edit in this repo.
2. Run `bash scripts/install-local.sh` to refresh your local install.
3. Test the change in Claude Code.
4. `git commit -am "..."` and `git push origin main`.
5. Other machines running `npx skills update curator` will get the new
   `SKILL.md`. To get the new hook, those users also re-run
   `bash scripts/install-local.sh` (or pull the file from the repo).

---

## License

MIT — see [LICENSE](LICENSE).
