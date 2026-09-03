# Hooks

This directory contains the companion `PostToolUse` hook that records every
skill activation to `~/.claude/skill-usage.log`. The hook is required for the
`/skills-curator` skill to produce meaningful call-frequency data.

## Files

| File | Purpose |
|---|---|
| `log-skill-usage.py` | PostToolUse hook script. Stdlib only, cross-platform. |

## What the hook listens for

| Tool | Trigger | Logged as |
|---|---|---|
| `Skill` | any tool call with non-empty `skill` parameter | `skill` invocation |
| `Read` | reading `**/SKILL.md` under `~/.claude/skills/` | `read` of `user:<name>` |
| `Read` | reading `**/SKILL.md` under `~/.claude/plugins/` | `read` of `plugin:<name>` |
| `Bash` | `npx skills <name>` invocation | `bash` of `plugin:<name>` |

All other tool calls are ignored.

## Install

The hook needs to be registered in `~/.claude/settings.json`. See the project
[README](../README.md) § "Install" for the exact snippet, or copy from
`../examples/settings.json` and edit.

For a one-liner install on macOS / Linux:

```bash
./scripts/install-hook.sh
```

On Windows PowerShell:

```powershell
.\scripts\install-hook.ps1
```

## Customizing the log location

By default the hook writes to `~/.claude/skill-usage.log`. Override with the
`SKILL_USAGE_LOG` environment variable if you want a per-project log:

```json
{
  "hooks": {
    "PostToolUse": [
      { "matcher": "Skill", "hooks": [
        { "type": "command",
          "command": "SKILL_USAGE_LOG=/tmp/skills.log python /path/to/log-skill-usage.py" }
      ]}
    ]
  }
}
```

## Privacy

The hook only reads `tool_input` from `stdin`. It does not read tool output,
file contents, transcript, or anything beyond what's already in the hook
payload. The log file is local and not transmitted anywhere.
