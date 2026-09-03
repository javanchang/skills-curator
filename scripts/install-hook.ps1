#!/usr/bin/env pwsh
# Idempotent installer for the skills-curator PostToolUse hook on Windows.
#
# Run from a PowerShell prompt at the repo root:
#
#   .\scripts\install-hook.ps1
#
# The script:
#   1. Copies hooks/log-skill-usage.py into ~/.claude/hooks/
#   2. Merges the PostToolUse hooks into ~/.claude/settings.json,
#      preserving any existing hooks the user has set up.
#
# Re-running is safe — existing entries are replaced, others are kept.

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$HookSrc  = Join-Path $RepoRoot "hooks\log-skill-usage.py"
$HookDst  = Join-Path $env:USERPROFILE ".claude\hooks\log-skill-usage.py"
$SettingsPath = Join-Path $env:USERPROFILE ".claude\settings.json"

if (-not (Test-Path $HookSrc)) {
    throw "Hook source not found at $HookSrc. Run from the repo root."
}

# 1. Copy the hook -----------------------------------------------------------
$HookDir = Split-Path $HookDst -Parent
if (-not (Test-Path $HookDir)) {
    New-Item -ItemType Directory -Path $HookDir -Force | Out-Null
}
Copy-Item -Path $HookSrc -Destination $HookDst -Force
Write-Host "Installed hook -> $HookDst"

# 2. Merge settings.json -----------------------------------------------------
if (-not (Test-Path $SettingsPath)) {
    @{} | ConvertTo-Json -Depth 10 | Set-Content -Path $SettingsPath -Encoding UTF8
}

$settings = Get-Content -Path $SettingsPath -Raw -Encoding UTF8 | ConvertFrom-Json

if (-not $settings.PSObject.Properties.Name -contains "hooks") {
    $settings | Add-Member -MemberType NoteProperty -Name "hooks" -Value ([pscustomobject]@{})
}
if (-not $settings.hooks.PSObject.Properties.Name -contains "PostToolUse") {
    $settings.hooks | Add-Member -MemberType NoteProperty -Name "PostToolUse" -Value @()
}

# Drop any prior entries that point at our hook path, so re-running is idempotent.
$existing = $settings.hooks.PostToolUse | Where-Object {
    -not ($_.hooks | Where-Object { $_.command -like "*log-skill-usage.py*" })
}
$existing += @(
    @{
        matcher = "Skill|Read|Bash"
        hooks   = @(
            @{
                type    = "command"
                command = "python `"$HookDst`""
            }
        )
    }
)
$settings.hooks.PostToolUse = $existing

$settings | ConvertTo-Json -Depth 10 | Set-Content -Path $SettingsPath -Encoding UTF8
Write-Host "Updated $SettingsPath (PostToolUse matcher: Skill|Read|Bash)"
Write-Host ""
Write-Host "Done. Restart Claude Code so the hook takes effect."
