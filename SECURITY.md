# Security Policy

## Supported versions

| Version | Supported          |
|---------|--------------------|
| 0.2.x   | ✅ Current         |
| 0.1.x   | ⚠️ Critical fixes only |
| < 0.1   | ❌                |

## Reporting a vulnerability

The hook reads from stdin and writes to `~/.claude/skill-usage.log`. The
biggest risks are:

- Path traversal in `Read` payloads (an attacker tricks the hook into reading
  outside `~/.claude/skills/` and `~/.claude/plugins/`). We guard against
  this with anchored regex; please report if you find a bypass.
- Arbitrary code execution via the `Bash` matcher (e.g. crafted `npx skills`
  command that shells out). We only **match** the command string — we never
  execute it — but please report if you find a regex bypass.

**Please don't file public issues for security problems.** Use
[GitHub Security Advisories](https://github.com/javanchang/skills-curator/security/advisories/new).
We'll respond within 72 hours.

## What we'll do

1. Acknowledge within 72 hours.
2. Triage and assign a CVSS-style severity.
3. Patch and release within 14 days for high/critical issues, 30 days for low/medium.
4. Credit you in the release notes (unless you ask to remain anonymous).
