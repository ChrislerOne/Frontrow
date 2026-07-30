"""The standalone pages: app-served 404/500/offline and the two oauth2-proxy templates.

The proxy templates can't be exercised through the app (the proxy renders them), so the
checks here are the ones that actually break in production: the Go template must be
balanced, and it must only use variables oauth2-proxy really passes.
"""

import html
import re
from pathlib import Path

import pytest

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
AUTH = FRONTEND / "auth"

# oauth2-proxy v7.15.3, pkg/app/pagewriter — the full set each template is given.
SIGN_IN_VARS = {"ProxyPrefix", "Redirect", "ProviderName", "SignInMessage", "CustomLogin",
                "StatusCode", "Footer", "LogoData", "Version"}
ERROR_VARS = {"StatusCode", "Title", "Message", "RequestID", "Redirect", "ProxyPrefix",
              "Footer", "Version"}


def test_404_is_served_for_an_unknown_page(client):
    r = client.get("/no-such-page")
    assert r.status_code == 404
    assert "That page isn't on the bill" in html.unescape(r.text)


def test_unknown_api_path_still_returns_json(client):
    r = client.get("/api/no-such-endpoint")
    assert r.status_code == 404 and r.headers["content-type"].startswith("application/json")


def test_offline_page_and_service_worker_are_reachable(client):
    assert "You're offline" in html.unescape(client.get("/offline.html").text)
    sw = client.get("/sw.js")
    assert sw.status_code == 200
    # It must never intercept anything but top-level navigations, or it starts serving
    # stale app content and swallowing the OAuth redirect.
    assert 'request.mode !== "navigate"' in sw.text
    assert '"/oauth2/"' in sw.text


def test_500_page_exists_and_names_no_internals(client):
    body = html.unescape((FRONTEND / "500.html").read_text())
    assert "Something broke backstage" in body
    assert "Traceback" not in body


def test_crash_returns_json_for_api_callers_and_leaks_nothing(crashing_client):
    r = crashing_client.post("/api/scrape", headers={"X-Forwarded-Email": "a@x.com"})
    assert r.status_code == 500 and r.json() == {"detail": "Internal server error"}
    assert "boom" not in r.text and "Traceback" not in r.text


@pytest.mark.parametrize("name,allowed", [("sign_in.html", SIGN_IN_VARS), ("error.html", ERROR_VARS)])
def test_proxy_template_is_balanced_and_uses_only_real_variables(name, allowed):
    src = html.unescape((AUTH / name).read_text())

    opens = len(re.findall(r"\{\{\s*(?:if|range|with|block|define)\b", src))
    ends = len(re.findall(r"\{\{\s*end\s*\}\}", src))
    assert opens == ends, f"{name}: {opens} block opens vs {ends} ends"

    used = set(re.findall(r"\{\{[^}]*?\.([A-Z]\w+)", src))
    assert used <= allowed, f"{name} uses variables oauth2-proxy doesn't pass: {used - allowed}"


def test_landing_starts_the_oauth_flow_the_way_the_proxy_expects():
    src = (AUTH / "sign_in.html").read_text()
    assert '<form method="GET" action="{{.ProxyPrefix}}/start">' in src
    assert 'name="rd" value="{{.Redirect}}"' in src


def test_access_denied_branch_exists_and_publishes_no_contact_address():
    src = html.unescape((AUTH / "error.html").read_text())
    assert "{{if eq .StatusCode 403}}" in src
    assert "This inbox isn't on the list" in src
    assert "mailto:" not in src  # an address on a public page is a spam magnet


def test_signed_out_landing_variant_matches_the_apps_sign_out_link():
    """The alert is gated on an exact string compare, so the two must agree or the
    variant silently never shows."""
    assert '{{if eq .Redirect "/?signed_out=1"}}' in (AUTH / "sign_in.html").read_text()
    assert "sign_out?rd=%2F%3Fsigned_out%3D1" in (FRONTEND / "index.html").read_text()


def test_standalone_pages_depend_on_no_external_assets():
    """These render when the app or the network is down — a CDN font or /nocturne.css
    would defeat the point."""
    for page in ("404.html", "500.html", "offline.html", "auth/sign_in.html", "auth/error.html"):
        src = (FRONTEND / page).read_text()
        assert "unpkg.com" not in src and "fonts.googleapis" not in src, page
        assert "nocturne.css" not in src, page
