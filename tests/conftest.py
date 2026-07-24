from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANALYZER = PROJECT_ROOT / "fst" / "artifacts" / "analyzer.hfstol"
GENERATOR = PROJECT_ROOT / "fst" / "artifacts" / "generator.hfstol"


def pytest_sessionstart(session) -> None:  # noqa: ARG001
    # Always rebuild: generated artifacts must never let stale lexical/tag
    # assumptions hide a source regression.
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "prepare_verbs.py")],
        cwd=PROJECT_ROOT,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "generate_lexc.py"),
            "--compile",
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )
