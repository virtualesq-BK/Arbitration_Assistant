"""Shared bootstrap for seed / ingest scripts: puts apps/api on sys.path so models import cleanly."""
from __future__ import annotations

import sys
from pathlib import Path

_here = Path(__file__).resolve()
ROOT = _here.parents[2]
API_DIR = ROOT / "apps" / "api"

# In Docker the scripts live at /app/scripts/… and the API code is at /app/ directly.
if not API_DIR.exists():
    API_DIR = _here.parents[2]  # /app itself

if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))
