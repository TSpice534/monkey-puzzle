"""Prod dev-secret boot guard (spec verification item 5).

These build their own one-off Config subclasses so they can simulate
DEBUG=False / TESTING=False (i.e. "real production") independently of
os.environ, without touching the process environment other tests rely on.
"""
import pytest

from app import create_app
from config import Config, _DEV_SECRET


def test_refuses_to_boot_in_prod_with_dev_secret():
    """Failure case: FLASK_DEBUG off, no SECRET_KEY set -> refuses to boot."""

    class ProdWithDevSecret(Config):
        DEBUG = False
        TESTING = False
        SECRET_KEY = _DEV_SECRET
        SQLALCHEMY_DATABASE_URI = 'sqlite://'

    with pytest.raises(RuntimeError):
        create_app(ProdWithDevSecret)


def test_boots_in_prod_with_a_real_secret_key():
    class ProdWithRealSecret(Config):
        DEBUG = False
        TESTING = False
        SECRET_KEY = 'a-genuinely-random-production-secret'
        SQLALCHEMY_DATABASE_URI = 'sqlite://'

    app = create_app(ProdWithRealSecret)
    assert app is not None

    with app.test_client() as client:
        response = client.get('/')
        assert response.status_code == 200
        # In prod mode (not app.debug), HSTS and upgrade-insecure-requests
        # must be present.
        assert 'Strict-Transport-Security' in response.headers
        assert 'upgrade-insecure-requests' in response.headers['Content-Security-Policy']


def test_dev_mode_bypasses_the_guard_even_with_dev_secret():
    class DevConfig(Config):
        DEBUG = True
        TESTING = False
        SECRET_KEY = _DEV_SECRET
        SQLALCHEMY_DATABASE_URI = 'sqlite://'

    # Should not raise: DEBUG=True means the guard never engages.
    app = create_app(DevConfig)
    assert app is not None
