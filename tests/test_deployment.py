from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

def test_container_port_and_healthcheck_are_consistent() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "EXPOSE 7860" in dockerfile
    assert '"--port", "7860"' in dockerfile
    assert "http://127.0.0.1:7860/health" in dockerfile

def test_container_uses_precompiled_transducers_and_non_root_user() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "USER user" in dockerfile
    assert "chown user:user /app" in dockerfile
    assert "fst/artifacts" in dockerfile
    assert "scripts/build_fst.sh" not in dockerfile
    assert "uv sync --frozen --no-dev" in dockerfile


def test_frontend_has_both_tools_and_no_external_runtime_assets() -> None:
    html = (PROJECT_ROOT / "static" / "index.html").read_text(encoding="utf-8")
    css = (PROJECT_ROOT / "static" / "app.css").read_text(encoding="utf-8")

    for element_id in (
        'id="analyze-form"',
        'id="generate-form"',
        'id="analyze-response"',
        'id="generate-response"',
    ):
        assert element_id in html

    assert '<script src="/app.js?v=20260731-1" defer></script>' in html
    assert '<link rel="stylesheet" href="/app.css" />' in html
    assert "fonts.googleapis.com" not in html
    assert "cdn." not in html

    font_path = PROJECT_ROOT / "static" / "assets" / "fonts" / "B_Kufigraph.ttf"
    assert font_path.is_file()
    assert font_path.stat().st_size > 0
    assert 'font-family: "B_Kufigraph"' in css
    assert "B Kufigraph" not in css
    assert "B.Kufigraph" not in css
