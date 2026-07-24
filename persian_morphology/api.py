"""FastAPI interface for normalization, analysis, and generation."""

from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from . import __version__
from .analyzer import Analyzer
from .generator import Generator
from .normalizer import normalize

APP_TITLE = "Persian Verbal Morphology"
APP_DESCRIPTION = (
    "Finite-state analysis and generation for the formal Persian verbal system "
    "described in the project's Distributed Morphology source."
)
SERVICE_UNAVAILABLE = {
    "code": "fst_unavailable",
    "message": "The compiled HFST transducers are unavailable.",
}

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=__version__,
)


class NonBlankModel(BaseModel):
    """Reject JSON strings that only contain whitespace."""

    @field_validator("*")
    @classmethod
    def reject_blank_strings(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("must contain a non-whitespace character")
        return value


class NormalizeRequest(NonBlankModel):
    text: Annotated[str, Field(min_length=1, max_length=2_000)]


class AnalyzeRequest(NonBlankModel):
    text: Annotated[str, Field(min_length=1, max_length=500)]
    normalize_input: bool = True
    max_analyses: Annotated[int, Field(ge=1, le=500)] = 100


class GenerateRequest(NonBlankModel):
    analysis: Annotated[str, Field(min_length=1, max_length=500)]
    max_forms: Annotated[int, Field(ge=1, le=500)] = 100


class WeightedResult(BaseModel):
    value: str
    weight: float


class HealthResponse(BaseModel):
    status: str
    version: str


class NormalizeResponse(BaseModel):
    input: str
    normalized: str
    changed: bool


class AnalyzeResponse(BaseModel):
    input: str
    normalized: str
    count: int
    truncated: bool
    analyses: list[WeightedResult]


class GenerateResponse(BaseModel):
    analysis: str
    count: int
    truncated: bool
    forms: list[WeightedResult]


class CapabilitiesResponse(BaseModel):
    language: str
    version: str
    scope: str
    analysis_schema: str
    coverage: list[str]
    deferred: list[str]


CAPABILITIES = CapabilitiesResponse(
    language="fa",
    version=__version__,
    scope="formal Persian verbal morphology",
    analysis_schema=(
        "ROOT+V[+PV=...][+Caus]+Tense/Mood/Aspect[+Neg]+Person+Number"
    ),
    coverage=[
        "infinitive and participle",
        "simple past and past progressive",
        "present indicative progressive",
        "present subjunctive and imperative",
        "present perfect and past perfect",
        "analytic future",
        "negation",
        "agreement",
        "source-supported preverbs and causatives",
    ],
    deferred=[
        "compound-verb recognition",
        "nominal and adjectival morphology",
        "clitics outside the implemented verbal paradigms",
        "sentence-level contextual disambiguation",
    ],
)


@lru_cache(maxsize=1)
def get_analyzer() -> Analyzer:
    return Analyzer()


@lru_cache(maxsize=1)
def get_generator() -> Generator:
    return Generator()


def _fst_unavailable(exc: FileNotFoundError) -> HTTPException:
    return HTTPException(status_code=503, detail=SERVICE_UNAVAILABLE)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Lightweight liveness endpoint used by the container health check."""

    return HealthResponse(status="ok", version=__version__)


@app.get("/api/capabilities", response_model=CapabilitiesResponse)
def capabilities() -> CapabilitiesResponse:
    """Describe the implemented linguistic scope without loading HFST."""

    return CAPABILITIES


@app.post("/api/normalize", response_model=NormalizeResponse)
def normalize_endpoint(request: NormalizeRequest) -> NormalizeResponse:
    normalized = normalize(request.text)
    return NormalizeResponse(
        input=request.text,
        normalized=normalized,
        changed=normalized != request.text,
    )


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze_endpoint(request: AnalyzeRequest) -> AnalyzeResponse:
    normalized = normalize(request.text) if request.normalize_input else request.text
    try:
        results = get_analyzer().analyze(
            normalized,
            normalize_input=False,
            max_analyses=request.max_analyses + 1,
        )
    except FileNotFoundError as exc:
        raise _fst_unavailable(exc) from exc

    truncated = len(results) > request.max_analyses
    visible_results = results[: request.max_analyses]
    return AnalyzeResponse(
        input=request.text,
        normalized=normalized,
        count=len(visible_results),
        truncated=truncated,
        analyses=[WeightedResult(**asdict(result)) for result in visible_results],
    )


@app.post("/api/generate", response_model=GenerateResponse)
def generate_endpoint(request: GenerateRequest) -> GenerateResponse:
    analysis = request.analysis.strip()
    try:
        results = get_generator().generate(analysis, max_forms=request.max_forms + 1)
    except FileNotFoundError as exc:
        raise _fst_unavailable(exc) from exc

    truncated = len(results) > request.max_forms
    visible_results = results[: request.max_forms]
    return GenerateResponse(
        analysis=analysis,
        count=len(visible_results),
        truncated=truncated,
        forms=[WeightedResult(**asdict(result)) for result in visible_results],
    )


STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
