"""404/500 render the custom error pages and still carry security headers."""


def test_404_renders_custom_page(client):
    response = client.get('/this-route-does-not-exist')
    assert response.status_code == 404
    body = response.get_data(as_text=True)
    assert 'Page not found' in body
    assert 'Back home' in body


def test_404_carries_security_headers(client):
    response = client.get('/this-route-does-not-exist')
    headers = response.headers
    assert headers['X-Frame-Options'] == 'DENY'
    assert headers['X-Content-Type-Options'] == 'nosniff'
    assert 'Content-Security-Policy' in headers


def test_500_renders_custom_page(client):
    response = client.get('/__raise_for_test__')
    assert response.status_code == 500
    body = response.get_data(as_text=True)
    assert 'Something went wrong' in body
    assert 'Error reference:' in body


def test_500_carries_security_headers(client):
    response = client.get('/__raise_for_test__')
    headers = response.headers
    assert headers['X-Frame-Options'] == 'DENY'
    assert headers['X-Content-Type-Options'] == 'nosniff'
    assert 'Content-Security-Policy' in headers
