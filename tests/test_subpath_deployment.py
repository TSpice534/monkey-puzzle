"""Regression tests for the subpath-deployment 404 (backlog #0006 follow-up).

Nginx's `location /monkey-puzzle { proxy_pass http://unix:/...sock; }` (no URI
after the socket) forwards the full, unstripped request path to Gunicorn,
including the `/monkey-puzzle` prefix. `ProxyFix(x_prefix=1)` only sets
`SCRIPT_NAME` from `X-Forwarded-Prefix` for correct `url_for()` generation —
it does not touch `PATH_INFO` — so every route 404s under the subpath deploy
unless something also strips the prefix back off `PATH_INFO`
(`app/__init__.py::_strip_script_name`).
"""


def test_plain_request_unaffected_by_prefix_stripping(client):
    """No X-Forwarded-Prefix header (local dev / domain-root deploy) — unchanged."""
    resp = client.get('/')
    assert resp.status_code == 200


def test_root_request_with_forwarded_prefix_resolves(client):
    """Simulates exactly what Nginx forwards for a subpath deploy: the full,
    unstripped path plus X-Forwarded-Prefix. Without the PATH_INFO strip this
    404s even though Nginx/Gunicorn are healthy."""
    resp = client.get('/monkey-puzzle', headers={'X-Forwarded-Prefix': '/monkey-puzzle'})
    assert resp.status_code == 200


def test_nested_route_with_forwarded_prefix_resolves(client):
    resp = client.get(
        '/monkey-puzzle/survey/start',
        headers={'X-Forwarded-Prefix': '/monkey-puzzle'},
    )
    assert resp.status_code in (302, 303)  # survey.start redirects to the first step


def test_generated_links_carry_the_prefix(client):
    """SCRIPT_NAME (set by ProxyFix from X-Forwarded-Prefix) must still make it
    into url_for()-generated links, confirming the PATH_INFO strip doesn't
    interfere with SCRIPT_NAME-based reverse URL building."""
    resp = client.get('/monkey-puzzle', headers={'X-Forwarded-Prefix': '/monkey-puzzle'})
    assert b'href="/monkey-puzzle/survey/start"' in resp.data
