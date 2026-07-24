"""Runtime wrapper around the optimized HFST generator."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock

import hfst

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GENERATOR = PROJECT_ROOT / "fst" / "artifacts" / "generator.hfstol"


@dataclass(frozen=True, slots=True)
class GeneratedForm:
    value: str
    weight: float


class Generator:
    """Load a generator once and perform thread-safe lookups."""

    def __init__(self, path: str | Path = DEFAULT_GENERATOR):
        self.path = Path(path)
        if not self.path.is_file() or self.path.stat().st_size == 0:
            raise FileNotFoundError(
                f"HFST generator not found at {self.path}. Run: ./scripts/build_fst.sh"
            )

        stream = hfst.HfstInputStream(str(self.path))
        try:
            self._transducer = stream.read()
        finally:
            stream.close()
        self._lock = Lock()

    def generate(self, analysis: str, *, max_forms: int = 100) -> list[GeneratedForm]:
        if max_forms < 1:
            raise ValueError("max_forms must be positive")
        with self._lock:
            paths = self._transducer.lookup(analysis)
        return [GeneratedForm(value=value, weight=float(weight)) for value, weight in paths][
            :max_forms
        ]
