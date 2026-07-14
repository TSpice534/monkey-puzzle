"""Security headers must be present on every response, including error
pages, and must carry a fresh CSP nonce per request."""
import re


def test_security_headers_present_on_home(client):
    response = client.get('/')
    headers = response.headers

    assert headers['X-Frame-Options'] == 'DENY'
    assert headers['X-Content-Type-Options'] == 'nosniff'
    assert headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'
    assert headers['Permissions-Policy'] == 'geolocation=(), microphone=(), camera=()'
    assert 'Content-Security-Policy' in headers


def test_csp_contains_per_request_nonce(client):
    response = client.get('/')
    csp = response.headers['Content-Security-Policy']
    match = re.search(r"nonce-([0-9a-f]{32})", csp)
    assert match, f"expected a nonce-<hex> token in CSP, got: {csp}"


def test_csp_nonce_differs_between_requests(client):
    csp_a = client.get('/').headers['Content-Security-Policy']
    csp_b = client.get('/').headers['Content-Security-Policy']
    nonce_a = re.search(r"nonce-([0-9a-f]{32})", csp_a).group(1)
    nonce_b = re.search(r"nonce-([0-9a-f]{32})", csp_b).group(1)
    assert nonce_a != nonce_b


def test_csp_allows_bootstrap_cdn(client):
    csp = client.get('/').headers['Content-Security-Policy']
    assert 'cdn.jsdelivr.net' in csp


def test_dev_mode_omits_hsts_and_upgrade_insecure(client):
    """The TestConfig fixture runs with DEBUG=True (dev mode): HSTS and
    upgrade-insecure-requests must NOT be sent, so local plain-HTTP static
    assets keep loading."""
    response = client.get('/')
    assert 'Strict-Transport-Security' not in response.headers
    assert 'upgrade-insecure-requests' not in response.headers['Content-Security-Policy']
