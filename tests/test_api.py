from __future__ import annotations

from fastapi.testclient import TestClient

import persian_morphology.api as api_module
from persian_morphology import __version__


client = TestClient(api_module.app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_capabilities_state_the_limited_verbal_scope() -> None:
    response = client.get("/api/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert payload["language"] == "fa"
    assert payload["scope"] == "formal Persian verbal morphology"
    assert "compound-verb recognition" in payload["deferred"]
    assert "+PV=..." in payload["analysis_schema"]


def test_normalize_reports_the_canonical_spelling() -> None:
    response = client.post("/api/normalize", json={"text": "نمي روم"})

    assert response.status_code == 200
    assert response.json() == {
        "input": "نمي روم",
        "normalized": "نمی‌روم",
        "changed": True,
    }


def test_analyze_returns_a_stable_exact_result_shape() -> None:
    response = client.post("/api/analyze", json={"text": "رفتم"})

    assert response.status_code == 200
    assert response.json() == {
        "input": "رفتم",
        "normalized": "رفتم",
        "count": 1,
        "truncated": False,
        "analyses": [{"value": "رو+V+Past+Ind+P1+Sg", "weight": 0.0}],
    }


def test_analyze_preserves_ambiguity() -> None:
    response = client.post("/api/analyze", json={"text": "رفته"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert {result["value"] for result in payload["analyses"]} == {
        "رو+V+Part",
        "رو+V+Pres+Ind+Perf+P3+Sg",
    }


def test_analysis_limit_reports_truncation() -> None:
    response = client.post(
        "/api/analyze",
        json={"text": "رفته", "max_analyses": 1},
    )

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["truncated"] is True


def test_generate_returns_a_form() -> None:
    response = client.post(
        "/api/generate",
        json={"analysis": "  رو+V+Past+Ind+P1+Sg  "},
    )

    assert response.status_code == 200
    assert response.json() == {
        "analysis": "رو+V+Past+Ind+P1+Sg",
        "count": 1,
        "truncated": False,
        "forms": [{"value": "رفتم", "weight": 0.0}],
    }


def test_blank_queries_are_rejected() -> None:
    analyze_response = client.post("/api/analyze", json={"text": "   "})
    generate_response = client.post("/api/generate", json={"analysis": "\t"})

    assert analyze_response.status_code == 422
    assert generate_response.status_code == 422


def test_missing_transducer_has_safe_service_error(monkeypatch) -> None:
    def missing_analyzer():
        raise FileNotFoundError("/private/path/analyzer.hfstol")

    monkeypatch.setattr(api_module, "get_analyzer", missing_analyzer)
    response = client.post("/api/analyze", json={"text": "رفتم"})

    assert response.status_code == 503
    assert response.json() == {"detail": api_module.SERVICE_UNAVAILABLE}
    assert "/private/path" not in response.text


def test_static_frontend_is_served() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert 'id="analyze-form"' in response.text
