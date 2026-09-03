#!/usr/bin/env bash
# install-hook.sh — register the skills-curator hook on macOS / Linux.
#
# Idempotent: re-running replaces the existing entry for this script.
# Backups the original settings.json to ~/.claude/settings.json.bak.
#
# NOTE: This script only registers the hook — it does NOT copy the hook
# file. For a one-shot install that also copies SKILL.md + hook + bin/,
# use scripts/install-local.sh instead.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$SCRIPT_DIR/../hooks/log-skill-usage.py"

if [ ! -f "$HOOK" ]; then
    echo "error: hook not found at $HOOK" >&2
    exit 1
fi

# Pick a Python that actually works (Windows / Git Bash has a stub
# `python3` that points at the Microsoft Store).
PY=""
for cand in python python3 py; do
    if command -v "$cand" >/dev/null 2>&1 && "$cand" -c "pass" >/dev/null 2>&1; then
        PY="$cand"; break
    fi
done
if [ -z "$PY" ]; then
    echo "error: no working python interpreter found" >&2
    exit 1
fi

SETTINGS="$HOME/.claude/settings.json"
mkdir -p "$(dirname "$SETTINGS")"

if [ ! -f "$SETTINGS" ]; then
    echo '{ "hooks": { "PostToolUse": [] } }' > "$SETTINGS"
fi

cp "$SETTINGS" "$SETTINGS.bak"

"$PY" - "$SETTINGS" "$HOOK" "$PY" <<'PY'
import json, sys
from pathlib import Path

settings_path = Path(sys.argv[1])
hook_path = sys.argv[2]
py = sys.argv[3]

try:
    cfg = json.loads(settings_path.read_text(encoding="utf-8"))
except Exception:
    cfg = {}

hooks = cfg.setdefault("hooks", {})
post = hooks.setdefault("PostToolUse", [])

# Remove any existing entries pointing at this exact script
post[:] = [
    h for h in post
    if not any(
        b.get("type") == "command"
        and hook_path in b.get("command", "")
        for b in h.get("hooks", [])
    )
]

# Add fresh entries for Skill / Read / Bash
for matcher in ("Skill", "Read", "Bash"):
    post.append({
        "matcher": matcher,
        "hooks": [{
            "type": "command",
            "command": f"{py} {hook_path}",
        }],
    })

settings_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"updated {settings_path}")
PY

echo "backup: $SETTINGS.bak"
echo "verify:  cat $SETTINGS | grep -A1 log-skill-usage"
