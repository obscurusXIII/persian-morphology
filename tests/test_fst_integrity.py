from pathlib import Path

from persian_morphology.analyzer import Analyzer
from persian_morphology.generator import Generator
from scripts.generate_lexc import build_entries, read_verbs

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERBS = PROJECT_ROOT / "data" / "lexicon" / "verbs.tsv"


def test_every_expanded_path_is_bidirectional() -> None:
    """Check every source-backed lexical/surface pair, not only golden samples."""

    analyzer = Analyzer()
    generator = Generator()
    entries = build_entries(read_verbs(VERBS))

    generated_cache: dict[str, set[str]] = {}
    analyzed_cache: dict[str, set[str]] = {}
    for lexical, intermediate_surface in entries:
        surface = intermediate_surface.replace("Dvd", "د").replace("Dvl", "ت")
        generated = generated_cache.setdefault(
            lexical,
            {result.value for result in generator.generate(lexical, max_forms=1_000)},
        )
        analyzed = analyzed_cache.setdefault(
            surface,
            {
                result.value
                for result in analyzer.analyze(surface, normalize_input=False, max_analyses=1_000)
            },
        )
        assert surface in generated
        assert lexical in analyzed
