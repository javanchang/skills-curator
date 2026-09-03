# Contributing

Thanks for considering a contribution. This project is small on purpose — please
keep it that way.

## Ground rules

1. **No new dependencies.** The hook and the skill only use the Python stdlib
   and `bash` builtins. Adding `requests` or `pyyaml` is a hard sell.
2. **Backward compatibility.** A user's existing `~/.claude/skill-usage.log`
   must keep working. If you change the log format, write a migration note in
   `docs/log-format.md` and bump the major version.
3. **No silent failures.** If the hook can't write the log, write to stderr.
   If the spec can't read the log, print a clear actionable message — never
   just `print(0)`.
4. **Test before submitting a PR.** `pytest` must be green.

## Development setup

```bash
git clone https://github.com/javanchang/skills-curator
cd skills-curator
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -v
```

## How to add a new log source

If you want the hook to recognize a new way skills get activated (e.g. a
hypothetical `McpSkill` tool):

1. Add a matcher in `hooks/log-skill-usage.py`'s `main()` for the new tool
   name.
2. Extract the skill name with the same `(kind, skill)` return shape.
3. Add a test in `tests/test_hook.py` using a fixture payload.
4. Update `docs/log-format.md` if you add new columns or sources.

## How to add a new verdict rule

Edit `SKILL.md` § "综合建议" and `docs/verdicts.md`. Keep the table
short — every rule should be defensible in one sentence. The current rules
favor keeping things; only suggest uninstall when the case is overwhelming.

## Release process

1. Bump version in `pyproject.toml` and add a `[X.Y.Z]` entry to
   `CHANGELOG.md`.
2. Tag: `git tag vX.Y.Z && git push --tags`.
3. CI will publish a GitHub release draft. Edit and publish.
4. Bump the version back to `X.Y.Z.dev0` (or similar) in `pyproject.toml`.

## Code of conduct

Be respectful. We're all just trying to keep our skill folders from becoming
graveyards of dead plugins.
