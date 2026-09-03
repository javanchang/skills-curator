# Idempotent local installer for skills-curator (Windows).
#
# Run from a PowerShell prompt:
#
#   .\scripts\install-local.ps1
#
# What it does:
#   1. Copy .\SKILL.md → $env:USERPROFILE\.claude\skills\curator\SKILL.md
#   2. Copy .\hooks\log-skill-usage.py → $env:USERPROFILE\.claude\hooks\log-skill-usage.py
#   3. Merge a PostToolUse hook into $env:USERPROFILE\.claude\settings.json
#   4. Copy .\bin\skills-curator → $env:USERPROFILE\bin\skills-curator
#   5. Print PATH hint if ~\bin is not on PATH
#
# Re-running is safe — every step is idempotent.

$ErrorActionPreference = "Stop"

$RepoRoot      = Resolve-Path (Join-Path $PSScriptRoot "..")
$SrcSkill      = Join-Path $RepoRoot "SKILL.md"
$SrcHook       = Join-Path $RepoRoot "hooks\log-skill-usage.py"
$SrcBin        = Join-Path $RepoRoot "bin\skills-curator"

$DestSkillDir  = Join-Path $env:USERPROFILE ".claude\skills\curator"
$DestSkill     = Join-Path $DestSkillDir "SKILL.md"
$DestHookDir   = Join-Path $env:USERPROFILE ".claude\hooks"
$DestHook      = Join-Path $DestHookDir "log-skill-usage.py"
$DestSettings  = Join-Path $env:USERPROFILE ".claude\settings.json"
$DestBinDir    = Join-Path $env:USERPROFILE "bin"
$DestBin       = Join-Path $DestBinDir "skills-curator"

foreach ($f in @($SrcSkill, $SrcHook, $SrcBin)) {
    if (-not (Test-Path $f)) {
        throw "Source file missing: $f. Run from inside the skills-curator repo."
    }
}

# 1. SKILL.md ---------------------------------------------------------------
if (-not (Test-Path $DestSkillDir)) {
    New-Item -ItemType Directory -Path $DestSkillDir -Force | Out-Null
}
Copy-Item -Path $SrcSkill -Destination $DestSkill -Force
Write-Host "✓ SKILL.md -> $DestSkill"

# 2. Hook -------------------------------------------------------------------
if (-not (Test-Path $DestHookDir)) {
    New-Item -ItemType Directory -Path $DestHookDir -Force | Out-Null
}
Copy-Item -Path $SrcHook -Destination $DestHook -Force
Write-Host "✓ hook -> $DestHook"

# 3. settings.json ----------------------------------------------------------
$SettingsDir = Split-Path $DestSettings -Parent
if (-not (Test-Path $SettingsDir)) {
    New-Item -ItemType Directory -Path $SettingsDir -Force | Out-Null
}
if (-not (Test-Path $DestSettings)) {
    '{}' | Set-Content -Path $DestSettings -Encoding UTF8
}

# Convert JSON safely with python (PowerShell's ConvertFrom-Json is fine,
# but the edit loop is shorter in python).
$env:PYTHONIOENCODING = "utf-8"

python - "$DestSettings" "$DestHook" <<'PY'
import json, sys
path, hook_path = sys.argv[1], sys.argv[2]

with open(path, "r", encoding="utf-8") as f:
    settings = json.load(f)

hooks = settings.setdefault("hooks", {})
post = hooks.get("PostToolUse") or []

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
            "command": f"python \"{hook_path}\"",
        }
    ],
})
hooks["PostToolUse"] = post

with open(path, "w", encoding="utf-8") as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(f"✓ settings.json PostToolUse updated (matcher: Skill|Read|Bash)")
PY

# 4. bin/skills-curator CLI ------------------------------------------------
if (-not (Test-Path $DestBinDir)) {
    New-Item -ItemType Directory -Path $DestBinDir -Force | Out-Null
}
Copy-Item -Path $SrcBin -Destination $DestBin -Force
Write-Host "✓ CLI -> $DestBin"

# 5. PATH hint --------------------------------------------------------------
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$DestBinDir*") {
    Write-Host ""
    Write-Host "NOTE: $DestBinDir is not on your PATH."
    Write-Host "Add it permanently with:"
    Write-Host "    [Environment]::SetEnvironmentVariable('Path', $env:Path + ';$DestBinDir', 'User')"
    Write-Host "Or for the current session only:"
    Write-Host "    `$env:Path += ';$DestBinDir'"
}

Write-Host ""
Write-Host "Done. Restart Claude Code so the hook takes effect."
Write-Host "Invoke the skill with: /curator"
Write-Host "Verify with:  Get-Content \$env:USERPROFILE\.claude\skill-usage.log"
