"""Shared pytest fixtures for the Monkey Puzzle test suite.

Tests run against `create_app` with an in-memory SQLite database and
`TESTING=True`, which also bypasses the production dev-secret boot guard
(the guard is exercised directly in test_prod_guard.py with its own
one-off app instances).
"""
import pytest

from app import create_app
from app import db as _db
from config import Config


class TestConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'  # in-memory, fresh per app instance


@pytest.fixture()
def app():
    application = create_app(TestConfig)
    # Route added purely for exercising the 500 error handler end-to-end
    # via the test client, without needing a real bug in production code.
    application.config['PROPAGATE_EXCEPTIONS'] = False

    @application.route('/__raise_for_test__')
    def _raise_for_test():
        raise RuntimeError('deliberate failure for 500 handler test')

    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    return _db
