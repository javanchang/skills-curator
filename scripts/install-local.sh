#!/usr/bin/env bash
# Idempotent local installer for skills-curator.
#
# Run from anywhere (it resolves the repo from its own location):
#
#   bash /path/to/skills-curator/scripts/install-local.sh
#
# What it does:
#   1. Copy ./SKILL.md → ~/.claude/skills/skills-curator/SKILL.md
#   2. Copy ./hooks/log-skill-usage.py → ~/.claude/hooks/log-skill-usage.py
#   3. Merge a PostToolUse hook into ~/.claude/settings.json
#   4. Copy ./bin/skills-curator → ~/.local/bin/skills-curator (and chmod +x)
#   5. Print PATH hint if ~/.local/bin is not already on PATH
#
# Re-running is safe — every step is idempotent.

set -euo pipefail

# --- Resolve paths ----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SRC_SKILL="${REPO_ROOT}/SKILL.md"
SRC_HOOK="${REPO_ROOT}/hooks/log-skill-usage.py"
SRC_BIN="${REPO_ROOT}/bin/skills-curator"

DEST_SKILL_DIR="${HOME}/.claude/skills/skills-curator"
DEST_SKILL="${DEST_SKILL_DIR}/SKILL.md"
DEST_HOOK_DIR="${HOME}/.claude/hooks"
DEST_HOOK="${DEST_HOOK_DIR}/log-skill-usage.py"
DEST_SETTINGS="${HOME}/.claude/settings.json"
DEST_BIN_DIR="${HOME}/.local/bin"
DEST_BIN="${DEST_BIN_DIR}/skills-curator"

for f in "$SRC_SKILL" "$SRC_HOOK" "$SRC_BIN"; do
  if [[ ! -f "$f" ]]; then
    echo "ERROR: $f not found. Run from inside the skills-curator repo." >&2
    exit 1
  fi
done

# --- 1. SKILL.md ------------------------------------------------------------
mkdir -p "$DEST_SKILL_DIR"
cp -f "$SRC_SKILL" "$DEST_SKILL"
echo "✓ SKILL.md → $DEST_SKILL"

# --- 2. Hook ----------------------------------------------------------------
mkdir -p "$DEST_HOOK_DIR"
cp -f "$SRC_HOOK" "$DEST_HOOK"
chmod +x "$DEST_HOOK"
echo "✓ hook → $DEST_HOOK"

# --- 3. settings.json -------------------------------------------------------
mkdir -p "$(dirname "$DEST_SETTINGS")"
if [[ ! -f "$DEST_SETTINGS" ]]; then
  printf '{}' > "$DEST_SETTINGS"
fi

# Pick a Python that exists. On Windows / Git Bash, `python3` may be a stub
# pointing at the Microsoft Store; prefer `python`, fall back to others.
PY=""
for cand in python python3 py; do
  if command -v "$cand" >/dev/null 2>&1; then
    if "$cand" -c "pass" >/dev/null 2>&1; then
      PY="$cand"; break
    fi
  fi
done
if [[ -z "$PY" ]]; then
  echo "ERROR: no working python interpreter found (tried: python python3 py)" >&2
  exit 1
fi

PYTHONIOENCODING=utf-8 "$PY" - "$DEST_SETTINGS" "$DEST_HOOK" "$PY" <<'PY'
import json, sys
path, hook_path = sys.argv[1], sys.argv[2]

with open(path, "r", encoding="utf-8") as f:
    settings = json.load(f)

hooks = settings.setdefault("hooks", {})
post = hooks.get("PostToolUse") or []

# Drop any prior entries that pointed at our hook — makes re-runs idempotent.
post = [
    e for e in post
    if not any(
        h.get("type") == "command" and hook_path in (h.get("command") or "")
        for h in (e.get("hooks") or [])
    )
]

post.append({
    "matcher": "Skill|Read|Bash",
    "hooks": [
        {
            "type": "command",
            # Use the python binary we already detected. On Windows,
            # this avoids the Microsoft Store stub for `python3`.
            "command": f"{sys.argv[3]} \"{hook_path}\"",
        }
    ],
})
hooks["PostToolUse"] = post

with open(path, "w", encoding="utf-8") as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(f"✓ settings.json PostToolUse updated (matcher: Skill|Read|Bash)")
PY

# --- 4. bin/skills-curator CLI ---------------------------------------------
mkdir -p "$DEST_BIN_DIR"
cp -f "$SRC_BIN" "$DEST_BIN"
chmod +x "$DEST_BIN"
echo "✓ CLI → $DEST_BIN"

# --- 5. PATH hint -----------------------------------------------------------
case ":$PATH:" in
  *":$DEST_BIN_DIR:"*) ;;
  *)
    echo ""
    echo "NOTE: $DEST_BIN_DIR is not on your PATH."
    echo "Add this to ~/.bashrc or ~/.zshrc:"
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    ;;
esac

echo ""
echo "Done. Restart Claude Code so the hook takes effect."
echo "Invoke the skill with: /skills-curator"
echo "Verify with:  cat ~/.claude/skill-usage.log"
