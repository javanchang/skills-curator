"""Pytest config for skills-curator.

Adds the repo root to sys.path so `tests` can import `hooks.log_skill_usage`
without installing the package.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
