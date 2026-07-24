"""FastAPI interface for normalization, analysis, and generation."""

from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from .analyzer import Analyzer
from .generator import Generator
from .normalizer import normalize

app = FastAPI(title="Persian Morphology", version=__version__)


class NormalizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2_000)


class AnalyzeRequest(NormalizeRequest):
    normalize_input: bool = True
    max_analyses: int = Field(default=100, ge=1, le=500)


class GenerateRequest(BaseModel):
    analysis: str = Field(min_length=1, max_length=500)
    max_forms: int = Field(default=100, ge=1, le=500)


@lru_cache(maxsize=1)
def get_analyzer() -> Analyzer:
    return Analyzer()


@lru_cache(maxsize=1)
def get_generator() -> Generator:
    return Generator()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.post("/api/normalize")
def normalize_endpoint(request: NormalizeRequest) -> dict[str, str]:
    return {"input": request.text, "normalized": normalize(request.text)}


@app.post("/api/analyze")
def analyze_endpoint(request: AnalyzeRequest) -> dict[str, object]:
    normalized = normalize(request.text) if request.normalize_input else request.text
    try:
        results = get_analyzer().analyze(
            normalized,
            normalize_input=False,
            max_analyses=request.max_analyses,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "input": request.text,
        "normalized": normalized,
        "analyses": [asdict(result) for result in results],
    }


@app.post("/api/generate")
def generate_endpoint(request: GenerateRequest) -> dict[str, object]:
    try:
        results = get_generator().generate(request.analysis, max_forms=request.max_forms)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "analysis": request.analysis,
        "forms": [asdict(result) for result in results],
    }


STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
