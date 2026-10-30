"""Public UI assets are explicitly allowlisted and contain no private files."""
import pytest


@pytest.mark.parametrize("filename", ["app.js", "i18n.js", "catalogue-en.js"])
def test_language_assets_are_public_javascript(client, filename):
    response = client.get(f"/app-assets/{filename}")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert response.headers["cache-control"] == "no-cache"
    assert response.text.strip()
    assert "DASHSCOPE_API_KEY=" not in response.text
    assert "LLM_API_KEY=" not in response.text


@pytest.mark.parametrize("path", [
    "/app-assets/.env", "/app-assets/index.html", "/app-assets/unknown.js",
    "/app-assets/%2e%2e%2f.env", "/app-assets/%2e%2e%2fmain.py",
])
def test_language_asset_route_does_not_expose_other_files(client, path):
    assert client.get(path).status_code == 404


def test_app_loads_languages_before_frontend_and_does_not_cache_stale_markup(client):
    response = client.get("/app")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-cache"
    html = response.text
    assert html.index('/app-assets/catalogue-en.js') < html.index('/app-assets/i18n.js')
    assert html.index('/app-assets/i18n.js') < html.index('/app-assets/app.js')
    assert 'id="language-zh"' in html
    assert 'id="language-en"' in html
