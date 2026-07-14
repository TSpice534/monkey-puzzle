import os

basedir = os.path.abspath(os.path.dirname(__file__))

# Sentinel used to detect an unchanged dev secret in production
_DEV_SECRET = 'dev-secret-change-in-production'


class Config:
    # Driven by FLASK_DEBUG (set in .flaskenv for local dev); off by default so the
    # dev-secret / HSTS guards below actually engage in production.
    DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'
    SECRET_KEY = os.environ.get('SECRET_KEY') or _DEV_SECRET
    _db_url = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'monkeypuzzle.db')
    # SQLAlchemy requires postgresql:// (some providers hand out postgres:// URLs)
    SQLALCHEMY_DATABASE_URI = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}

    # ------------------------------------------------------------------
    # Session / cookie security
    # SESSION_COOKIE_SECURE requires HTTPS — set HTTPS=true in production
    # ------------------------------------------------------------------
    _https = os.environ.get('HTTPS', 'false').lower() == 'true'

    SESSION_COOKIE_HTTPONLY  = True
    SESSION_COOKIE_SAMESITE  = 'Lax'
    SESSION_COOKIE_SECURE    = _https

    # ------------------------------------------------------------------
    # Survey content — single source of truth for questions/personas/scoring,
    # owned by Rob and Andrew. Env-overridable so tests can point at a
    # fixture file without touching the real content.
    # ------------------------------------------------------------------
    SURVEY_PATH = os.environ.get('SURVEY_PATH') or os.path.join(basedir, 'content', 'survey.yaml')
