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

    # ------------------------------------------------------------------
    # Mail — optional "email me a copy" (Phase 5). Left unset by default;
    # the email route checks MAIL_SERVER and no-ops with a flash message
    # rather than raising if it isn't configured.
    # ------------------------------------------------------------------
    MAIL_SERVER   = os.environ.get('MAIL_SERVER')
    MAIL_PORT     = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS  = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_USERNAME')

    # ------------------------------------------------------------------
    # Rate limiting (Phase 5) — only the email-a-copy endpoint is limited;
    # it is the one route that can send outbound mail on an anonymous,
    # no-account request, so it is the one abuse surface worth guarding.
    # ------------------------------------------------------------------
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')
