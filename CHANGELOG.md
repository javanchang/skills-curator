# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-09-03

### Changed
- **Project renamed `skill-audit` → `skills-curator`** (Claude Code slash command
  is `/skills-curator`). Name chosen because the tool doesn't only audit — it actively
  curates (gives keep / prune recommendations) — and `skills-curator` had no
  GitHub collisions at the time of release.
- Skill rewritten to use embedded Python heredocs instead of `awk`.
  awk's `$2`/`$5` indexing broke silently when the log format changed. The new
  Python block auto-detects 2/3/4/5-column log formats.
- Each bash block now exports `PYTHONIOENCODING=utf-8` so output never mojibakes
  in non-UTF-8 default locales.
- Skill spec deduplicates per `(session, kind, skill)` triple so auto-loaded
  skill bursts don't inflate call counts.

### Added
- `docs/log-format.md` — formal spec for `~/.claude/skill-usage.log`.
- `tests/test_format_detection.py` — regression suite over 6 fixtures
  (2/3/4/5-col, empty, missing, mixed).
- `tests/test_hook.py` — unit tests for `log-skill-usage.py` debounce and
  path parsing.
- `.github/workflows/test.yml` — CI runs pytest on push/PR.
- `scripts/install-local.{sh,ps1}` — one-shot install that copies SKILL.md,
  hook, settings.json merge, and CLI in a single idempotent command.

## [0.1.0] - 2026-08-XX

### Added
- Initial release: skill that reports disk usage + call counts from
  `~/.claude/skill-usage.log`.
- Companion PostToolUse hook (`hooks/log-skill-usage.py`) that logs Skill tool
  calls, SKILL.md Reads, and `npx skills <name>` Bash invocations.
- 5-second debounce on `(session, kind, skill)` to suppress auto-load bursts.

[Unreleased]: https://github.com/javanchang/skills-curator/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/javanchang/skills-curator/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/javanchang/skills-curator/releases/tag/v0.1.0
