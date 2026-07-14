from flask import Blueprint

bp = Blueprint('survey', __name__, url_prefix='/survey')

from app.survey import routes  # noqa: E402, F401
