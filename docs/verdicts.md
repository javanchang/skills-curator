# Verdict rules

The audit report (`/skills-curator`) tags every installed skill with one of:

- **保留** (keep) — used at least once per week
- **建议卸载** (suggest uninstall) — large and never / rarely used
- **保留（询问用户确认）** — sparse but worth confirming case-by-case

## The rules, in priority order

| # | Condition                                                  | Verdict   | Rationale                                                              |
|---|------------------------------------------------------------|-----------|------------------------------------------------------------------------|
| 1 | ≥ 1 call/week                                              | 保留      | You're actively using it.                                              |
| 2 | size > 1 MB **and** unused for ≥ 30 days                   | 建议卸载  | Big and dormant — almost certainly safe to delete.                      |
| 3 | size > 5 MB **and** never called                           | 建议卸载  | No upside, real cost.                                                   |
| 4 | sparsely called, but each call saves obvious time          | 保留\*    | Some skills fire rarely but their workflow is hard to reproduce — flag for user. |
| 5 | never seen in log **and** size > 100 KB                    | 建议卸载  | Likely something you installed once and forgot.                       |

\* Rule 4 is the only one that requires asking the user. The other four are
mechanical and applied automatically.

## Why these thresholds?

The numbers are conservative defaults that worked well in practice for a
single-developer setup:

- **1 MB / 30 days** — Most actively-used skills are <100 KB. Anything
  bigger is either a bundled binary, a node_modules tree, or a long-form
  doc set. If you've not touched it in a month, you're probably not
  going to.
- **5 MB / never** — This is the "abandoned experiment" tier. Lots of
  plugins pull in 5-20 MB of dependencies that are useless without the
  plugin code being exercised.
- **100 KB floor** — Below this, even a never-used skill costs almost
  nothing. Don't be precious about deleting 50 KB files.

## Tweak the thresholds

The verdict logic lives in the `/skills-curator` skill (`SKILL.md` at the repo root).
Edit the thresholds table there if your situation is different
(e.g. you're on a tiny SSD and want the 30-day window shortened).

## What the verdict is *not*

- It is **not** a security review. A skill being "保留" does not mean it
  is safe. Audit trust separately.
- It is **not** a recommendation about which skills are *best*. A
  high-quality skill you never use should still be deleted.
- It is **not** an automatic action. The script only writes the report
  — it never deletes anything for you.
