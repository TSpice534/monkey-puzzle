import secrets

from flask import Flask, g
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from config import Config, _DEV_SECRET

db = SQLAlchemy()
migrate = Migrate()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Trust one layer of reverse-proxy headers (Nginx).
    # x_prefix honours SCRIPT_NAME set by Gunicorn for subpath deployments.
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    db.init_app(app)
    migrate.init_app(app, db)

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    # ------------------------------------------------------------------
    # Security headers (Cyber Essentials L1)
    # A per-request nonce is generated in before_request and injected
    # into the CSP script-src and into all Jinja2 templates via the
    # context processor below. This lets us drop 'unsafe-inline' from
    # script-src while still running inline Chart.js / UI scripts.
    # 'unsafe-inline' is intentionally retained for style-src because
    # Bootstrap and templates use many style= attributes that cannot
    # take nonces; inline styles cannot execute code.
    # ------------------------------------------------------------------
    @app.before_request
    def _set_csp_nonce():
        g.csp_nonce = secrets.token_hex(16)

    @app.context_processor
    def _inject_csp_nonce():
        return {'csp_nonce': g.get('csp_nonce', '')}

    @app.after_request
    def set_security_headers(response):
        nonce = g.get('csp_nonce', '')
        csp_parts = [
            "default-src 'self'",
            f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
            "font-src 'self' https://cdn.jsdelivr.net",
            "img-src 'self' data:",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "object-src 'none'",
        ]
        if not app.debug:
            # Only upgrade HTTP→HTTPS in production where TLS is available.
            # Including this in local dev causes Safari to reject plain-HTTP static files.
            csp_parts.append("upgrade-insecure-requests")
        csp = "; ".join(csp_parts)
        response.headers['X-Frame-Options']           = 'DENY'
        response.headers['X-Content-Type-Options']    = 'nosniff'
        response.headers['Referrer-Policy']           = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy']        = 'geolocation=(), microphone=(), camera=()'
        response.headers['Content-Security-Policy']   = csp
        if not app.debug:
            # HSTS — only set over HTTPS; do not send in local dev
            response.headers['Strict-Transport-Security'] = (
                'max-age=31536000; includeSubDomains; preload'
            )
        return response

    if not app.debug and not app.testing:
        # Refuse to start in production with the default dev secret
        if app.config['SECRET_KEY'] == _DEV_SECRET:
            raise RuntimeError(
                'SECRET_KEY is set to the development default. '
                'Set a secure SECRET_KEY environment variable before deploying.'
            )

    return app


from app import models  # noqa: E402, F401
