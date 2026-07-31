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
    assert '/assets/images/vakav-favicon-framed.png' in response.text
    assert '/app.js?v=20260731-1' in response.text

    favicon = client.get("/assets/images/vakav-favicon-framed.png")
    assert favicon.status_code == 200
    assert favicon.headers["content-type"] == "image/png"
    assert favicon.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_frontend_fonts_are_served_and_declared_correctly() -> None:
    css = client.get("/app.css")

    assert css.status_code == 200
    for filename in (
        "w_Yekan.ttf",
        "w_Yekan Italic.ttf",
        "w_Yekan Bold.ttf",
        "w_Yekan Black.ttf",
    ):
        assert f'/assets/fonts/{filename}' in css.text
        font = client.get(f"/assets/fonts/{filename}")
        assert font.status_code == 200
        assert font.content

    assert "font-style: bold" not in css.text
    assert "font-style: bolder" not in css.text


def test_footer_version_markup_and_display_are_stable() -> None:
    html = client.get("/")
    javascript = client.get("/app.js")

    assert 'id="version-dash">-</b>' in html.text
    assert 'id="app-version" dir="ltr">۰.۲</b>' in html.text
    assert "appVersion.textContent" not in javascript.text


def test_frontend_health_check_recovers_from_render_cold_starts() -> None:
    javascript = client.get("/app.js")

    assert javascript.status_code == 200
    assert "serviceRetryDelays" in javascript.text
    assert 'cache: "no-store"' in javascript.text
    assert 'payload.status !== "ok"' in javascript.text
    assert 'setServiceState("checking", "در حال اتصال به سامانه")' in javascript.text
    assert "serviceLastSuccessfulAt" in javascript.text
    assert javascript.text.count("markServiceAvailable();") >= 2
    assert 'window.addEventListener("online"' in javascript.text
