"""Terminal and ASGI entry point."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from persian_morphology.analyzer import Analyzer
from persian_morphology.api import app  # noqa: F401 -- exported for uvicorn main:app
from persian_morphology.generator import Generator
from persian_morphology.normalizer import normalize

PROJECT_ROOT = Path(__file__).resolve().parent


def _joined_text(parts: list[str]) -> str:
    return " ".join(parts)


def _build() -> None:
    environment = {**os.environ, "PYTHON_BIN": sys.executable}
    subprocess.run(
        [str(PROJECT_ROOT / "scripts" / "build_fst.sh")],
        check=True,
        env=environment,
    )


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="persian-morphology")
    subparsers = parser.add_subparsers(dest="command", required=True)

    normalize_parser = subparsers.add_parser("normalize", help="normalize Persian text")
    normalize_parser.add_argument("text", nargs="+")

    analyze_parser = subparsers.add_parser("analyze", help="analyze a Persian word")
    analyze_parser.add_argument("text", nargs="+")
    analyze_parser.add_argument("--no-normalize", action="store_true")
    analyze_parser.add_argument("--json", action="store_true")
    analyze_parser.add_argument("--max", type=int, default=100, dest="max_analyses")

    generate_parser = subparsers.add_parser("generate", help="generate forms from an analysis")
    generate_parser.add_argument("analysis")
    generate_parser.add_argument("--json", action="store_true")
    generate_parser.add_argument("--max", type=int, default=100, dest="max_forms")

    subparsers.add_parser("build", help="prepare data and compile HFST artifacts")

    serve_parser = subparsers.add_parser("serve", help="start the FastAPI server")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)

    if args.command == "normalize":
        print(normalize(_joined_text(args.text)))
        return 0

    if args.command == "build":
        _build()
        return 0

    if args.command == "analyze":
        query = _joined_text(args.text)
        results = Analyzer().analyze(
            query,
            normalize_input=not args.no_normalize,
            max_analyses=args.max_analyses,
        )
        if args.json:
            print(json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2))
        elif not results:
            print("NO_ANALYSIS")
        else:
            for result in results:
                print(f"{result.value}\t{result.weight:g}")
        return 0

    if args.command == "generate":
        results = Generator().generate(args.analysis, max_forms=args.max_forms)
        if args.json:
            print(json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2))
        elif not results:
            print("NO_FORM")
        else:
            for result in results:
                print(f"{result.value}\t{result.weight:g}")
        return 0

    if args.command == "serve":
        import uvicorn

        uvicorn.run("main:app", host=args.host, port=args.port, reload=False)
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(cli())
