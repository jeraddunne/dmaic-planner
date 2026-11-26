"""DMAIC Planner web app (ARI 410/510 Phase 3).

    python -m app.main          # from the repository root

Everything except app/main.py runs without Gradio, so the input checks and the
predictor contract can be tested with the project's own test runner.
"""
from __future__ import annotations

import sys
from pathlib import Path

# The rules engine and the Phase 3 models live in src/dmaic_planner. Put src/ on
# the import path so `python -m app.main` works from a fresh clone and in the
# Docker image without anyone setting PYTHONPATH.
_SRC = Path(__file__).resolve().parents[1] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
