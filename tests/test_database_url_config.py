"""Regression test for a production incident: `.flaskenv` used to set a relative
`DATABASE_URL=sqlite:///monkeypuzzle.db`. Flask-SQLAlchemy 3.x resolves relative
sqlite URLs against `app.instance_path`, not the process's working directory —
so `flask db upgrade` (which loads `.flaskenv`) silently migrated
`instance/monkeypuzzle.db`, while Gunicorn in production (which never loads
`.flaskenv`, and has no `DATABASE_URL` in its `.env`) fell back to `config.py`'s
absolute default and ran against a completely different, un-migrated file —
causing "no such table" 500s despite migrations reporting success.
"""
import os

_REPO_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def test_flaskenv_does_not_set_a_relative_database_url():
    flaskenv_path = os.path.join(_REPO_ROOT, '.flaskenv')
    with open(flaskenv_path) as f:
        for line in f:
            line = line.split('#', 1)[0].strip()
            if line.startswith('DATABASE_URL='):
                value = line.split('=', 1)[1]
                assert value.startswith('sqlite:////') or not value.startswith('sqlite:'), (
                    '.flaskenv must not set a relative sqlite:/// DATABASE_URL — '
                    'Flask-SQLAlchemy resolves it against app.instance_path, not '
                    'the CWD, which silently diverges from what Gunicorn uses in '
                    'production. Leave DATABASE_URL unset (falls back to the '
                    "absolute default in config.py) or use an absolute sqlite:////  URL."
                )


def test_default_database_uri_is_absolute(monkeypatch):
    """Guards config.py's own fallback: with no DATABASE_URL set at all, the
    default sqlite URI it builds must be absolute, so every context (local dev,
    CLI commands, Gunicorn) resolves to the identical file regardless of how
    Flask-SQLAlchemy's instance-path resolution treats relative paths."""
    monkeypatch.delenv('DATABASE_URL', raising=False)
    import importlib
    import config as config_module
    importlib.reload(config_module)
    try:
        uri = config_module.Config.SQLALCHEMY_DATABASE_URI
        assert uri.startswith('sqlite:////'), (
            f'Expected an absolute sqlite:////  URI, got {uri!r}'
        )
    finally:
        importlib.reload(config_module)
