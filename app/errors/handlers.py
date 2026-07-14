import uuid

from flask import render_template, current_app

from app.errors import bp


@bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html', title='Page Not Found'), 404


@bp.app_errorhandler(500)
def internal_error(error):
    from app import db
    db.session.rollback()
    error_id = uuid.uuid4().hex[:8].upper()
    current_app.logger.error('Unhandled exception [%s]', error_id, exc_info=error)
    return render_template('errors/500.html', title='Server Error', error_id=error_id), 500
