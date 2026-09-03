---
name: curator
description: 策展已安装的 Claude/Codex/agent skills——展示磁盘占用、调用频次，给出保留/卸载建议。
---

策展用户已安装的 skill。按以下顺序执行命令并生成报告。

> 每个 bash 代码块开头都自带 `export PYTHONIOENCODING=utf-8`，
> 不依赖调用方的 locale，**直接复制粘贴即可运行**，输出中文不会乱码。

## 1. 磁盘占用

```bash
du -sh ~/.claude/skills/*/ 2>/dev/null | sort -h
```

## 2. 调用次数（来自 hook 日志）

```bash
export PYTHONIOENCODING=utf-8
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

LOG=~/.claude/skill-usage.log

if [ ! -f "$LOG" ]; then
  echo "尚未启用 skill-usage hook，请先配置 PostToolUse。"
  echo "→ 在 ~/.claude/settings.json 的 hooks.PostToolUse 里匹配 Skill/Read/Bash，"
  echo "  命令执行：python <HOOK_PATH>"
  echo "  其中 <HOOK_PATH> = ~/.claude/hooks/log-skill-usage.py"
  echo "  Windows 用户把 ~ 替换为 %USERPROFILE%。"
  echo "→ 配置后跑几次 skill，再跑本审计命令。"
else
  python - "$LOG" <<'PY'
"""Skill usage stats — auto-detects 2/3/4/5-column log formats.

Format history:
  v1 (2-col):  <ts>\t<skill>
  v2 (3-col):  <ts>\t<source>\t<skill>
  v3 (4-col):  <ts>\t<session>\t<source>\t<skill>
  v4 (5-col):  <ts>\t<session>\t<source>\t<kind>\t<skill>   ← current

Dedup: per (session, kind-or-source, skill). Same row_key within a session
counts as ONE activation, so auto-load bursts don't multiply.
"""
import sys
from collections import Counter
from pathlib import Path

log = Path(sys.argv[1])
lines = [ln.rstrip("\n") for ln in log.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]

if not lines:
    print("（日志存在但内容为空——hook 已配置但尚未记录任何 skill 激活。）")
    sys.exit(0)

def row_key(parts):
    n = len(parts)
    if n >= 5:
        return f"{parts[3]}:{parts[4]}" if parts[3] else parts[4]
    if n == 4: return parts[3]
    if n == 3: return parts[2]
    if n == 2: return parts[1]
    return "?"

buckets = Counter()
seen = set()
for ln in lines:
    parts = ln.split("\t")
    session = parts[1] if len(parts) >= 3 else "legacy"
    key = row_key(parts)
    if (session, key) not in seen:
        seen.add((session, key))
        buckets[key] += 1

total = sum(buckets.values())
print(f"（共 {total} 次激活，去重后 {len(buckets)} 个 skill/skill-kind）")
print()
for key, count in buckets.most_common():
    print(f"  {count:>4}  {key}")
PY
fi
```

## 3. 30 天未调用

```bash
export PYTHONIOENCODING=utf-8
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

LOG=~/.claude/skill-usage.log

if [ ! -f "$LOG" ]; then
  echo "（hook 未启用，跳过本步）"
else
  python - "$LOG" <<'PY'
import sys
from datetime import datetime, timedelta
from pathlib import Path

log = Path(sys.argv[1])
lines = [ln for ln in log.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
if not lines:
    print("（日志为空）")
    sys.exit(0)

cutoff = datetime.now() - timedelta(days=30)

def skill_of(line):
    parts = line.split("\t")
    n = len(parts)
    if n >= 5: return f"{parts[3]}:{parts[4]}" if parts[3] else parts[4]
    if n == 4: return parts[3]
    if n == 3: return parts[2]
    if n == 2: return parts[1]
    return None

unused, used = set(), set()
for ln in lines:
    parts = ln.split("\t")
    try:
        ts = datetime.fromisoformat(parts[0])
    except ValueError:
        continue
    s = skill_of(ln)
    if not s:
        continue
    (unused if ts < cutoff else used).add(s)

stale = unused - used
if not stale:
    print("（30 天以上未调用的 skill：无）")
else:
    for s in sorted(stale):
        print(s)
PY
fi
```

## 4. 综合建议

输出一个表格，列：skill | 占用 | 调用次数 | 末次调用 | 判定。

判定规则：
- 调用 ≥ 1次/周 → **保留**
- 占用 > 1MB 且 30 天未调用 → **建议卸载**
- 占用 > 5MB 且从未调用 → **建议卸载**
- 调用稀疏但单次明显省时 → **保留**（询问用户确认）
- 从未出现且占用 > 100K → **建议卸载**

如果第 2 步显示 hook 未启用，告诉用户安装方法：

> 在 `~/.claude/settings.json` 加 `hooks.PostToolUse`，匹配 `Skill` /
> `Read` / `Bash`，命令执行
> `python <HOOK_PATH>`，
> 其中 `<HOOK_PATH>` 是本仓库 `hooks/log-skill-usage.py` 复制到目标机器后的位置
> （Linux/macOS 典型：`~/.claude/hooks/log-skill-usage.py`；
> Windows 典型：`%USERPROFILE%\.claude\hooks\log-skill-usage.py`）。
>
> **直接安装**：本仓库自带一键脚本
> （Linux/macOS `bash scripts/install-local.sh`，
> Windows PowerShell `.\scripts\install-local.ps1`）。
> 脚本会幂等地：拷贝 `SKILL.md` 到 `~/.claude/skills/curator/`，
> 拷贝 `hooks/log-skill-usage.py` 到 `~/.claude/hooks/`，
> 合并 `hooks.PostToolUse` 到 `~/.claude/settings.json`，
> 拷贝 `bin/skills-curator` 到 `~/.local/bin/`（Windows: `~\bin\`）并加入 `PATH` 提示。
>
> 安装后**主动调用一次** `/curator` 或任何 skill，验证日志是否落盘：
> ```bash
> cat ~/.claude/skill-usage.log
> ```
> 如果文件不存在 → 检查 settings.json 是否保存、解释器路径是否正确；
> 如果文件存在但本审计输出仍为空 → 把日志 mtime 和最近一次 skill 调用的
> 时间对比，确认 hook 是否被实际触发。

最后给出"可立即删除"清单（一句话 + 总共可释放空间）。

## 复现矩阵（debug 速查）

| 现象 | 原因 | 修法 |
|---|---|---|
| 第 2 步报"hook 未启用" | `~/.claude/skill-usage.log` 不存在 | 按上方"安装方法"配置 |
| 日志存在但显示"内容为空" | hook 配错或没被触发 | `ls -la ~/.claude/skill-usage.log`，mtime 早于最近一次 skill 调用 → 修 hook |
| 输出中文乱码 | （旧版已知问题） | 当前版本已在每个 bash 块头部自带 `PYTHONIOENCODING=utf-8`，不应再出现 |
| 30 天未调用显示为空但理应有数据 | 全部激活都在 30 天内 | 正常，等待数据老化 |
| skill 计数与直觉不符 | 同 session 内多次激活同一 skill 会被去重为 1 次 | 这是预期行为，避免自动加载时"看起来调用了 5 次" |
