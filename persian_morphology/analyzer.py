"""Runtime wrapper around the optimized HFST analyzer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock

import hfst

from .normalizer import normalize

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANALYZER = PROJECT_ROOT / "fst" / "artifacts" / "analyzer.hfstol"


@dataclass(frozen=True, slots=True)
class Analysis:
    value: str
    weight: float


class Analyzer:
    """Load an analyzer once and perform thread-safe lookups."""

    def __init__(self, path: str | Path = DEFAULT_ANALYZER):
        self.path = Path(path)
        if not self.path.is_file() or self.path.stat().st_size == 0:
            raise FileNotFoundError(
                f"HFST analyzer not found at {self.path}. Run: ./scripts/build_fst.sh"
            )

        stream = hfst.HfstInputStream(str(self.path))
        try:
            self._transducer = stream.read()
        finally:
            stream.close()
        self._lock = Lock()

    def analyze(
        self,
        text: str,
        *,
        normalize_input: bool = True,
        max_analyses: int = 100,
    ) -> list[Analysis]:
        if max_analyses < 1:
            raise ValueError("max_analyses must be positive")

        query = normalize(text) if normalize_input else text
        with self._lock:
            paths = self._transducer.lookup(query)

        return [Analysis(value=value, weight=float(weight)) for value, weight in paths][
            :max_analyses
        ]
