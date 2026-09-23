from flask import render_template

from app.main import bp
from app.survey.loader import SurveyConfigError, get_survey


@bp.route('/')
def index():
    try:
        personas = get_survey()['personas']
    except SurveyConfigError:
        personas = None          # home page must still render if survey.yaml is broken
    return render_template('index.html', title='Home', personas=personas)
