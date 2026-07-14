"""Happy path: the home route renders with no auth required."""


def test_index_returns_200(client):
    response = client.get('/')
    assert response.status_code == 200


def test_index_renders_landing_content(client):
    response = client.get('/')
    body = response.get_data(as_text=True)
    assert 'The Monkey Puzzle' in body
    # Confirms base.html's title block picked up the route's title=...
    assert '<title>Home' in body


def test_index_has_no_auth_or_client_chrome(client):
    """No login/dashboard/account nav items and no client-config leakage.

    Checks for actual auth-related UI markers (links, nav items, template
    variable leakage) rather than a bare substring match, since the
    landing copy legitimately describes the tool as "no-login".
    """
    body = client.get('/').get_data(as_text=True)
    for forbidden in (
        'href="/login"',
        'href="/dashboard"',
        '>Login<',
        '>Log in<',
        '>Dashboard<',
        'current_user',
    ):
        assert forbidden not in body
