"""Route tests for the new question types added for backlog #0003: the
interactive persona grid (mandatory to advance, grid-direct classification),
`triangle`, `multi_exact`, and per-audience option wording. Uses
tests/fixtures/survey_grid.yaml (5 steps: respondent_type, q_worded,
q_triangle, q_multi_exact, profile_grid)."""
import os

import pytest

from app.models import Submission
from app.survey.loader import clear_survey_cache

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'survey_grid.yaml')

INDIVIDUAL = 0  # option index for "As an individual"
ORGANISATION = 1  # option index for "On behalf of an organisation"


@pytest.fixture(autouse=True)
def _use_fixture_survey(app):
    app.config['SURVEY_PATH'] = FIXTURE_PATH
    clear_survey_cache()
    yield
    clear_survey_cache()


def _start_new(client):
    response = client.get('/survey/start')
    assert response.status_code == 302
    return response.headers['Location'].split('/survey/')[1].split('/step/')[0]


def _answer_up_to_grid(client, token, audience=INDIVIDUAL, worded_index=0):
    """POST steps 1-4 (router, q_worded, q_triangle, q_multi_exact), leaving
    step 5 (profile_grid) unanswered."""
    client.post(f'/survey/{token}/step/1', data={'respondent_type': str(audience)})
    client.post(f'/survey/{token}/step/2', data={'q_worded': str(worded_index)})
    client.post(f'/survey/{token}/step/3', data={'q_triangle': '0'})
    client.post(f'/survey/{token}/step/4', data={'q_multi_exact': ['0', '1']})


# ---------------------------------------------------------------------------
# Grid — persistence and grid-direct classification
# ---------------------------------------------------------------------------

def test_grid_step_post_persists_selected_cell(client, db):
    token = _start_new(client)
    _answer_up_to_grid(client, token)
    client.post(f'/survey/{token}/step/5', data={'profile_grid': '1,1'})

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.answers['profile_grid'] == [1, 1]


def test_completing_survey_classifies_to_the_grid_mapped_persona(client, db):
    token = _start_new(client)
    _answer_up_to_grid(client, token)
    final = client.post(f'/survey/{token}/step/5', data={'profile_grid': '1,1'})  # -> entrepreneur

    assert final.status_code == 302
    assert final.headers['Location'].endswith(f'/survey/{token}/result')

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.persona_id == 'entrepreneur'


# ---------------------------------------------------------------------------
# Grid — mandatory to advance
# ---------------------------------------------------------------------------

def test_grid_step_with_no_selection_rerenders_without_advancing(client, db):
    token = _start_new(client)
    _answer_up_to_grid(client, token)
    response = client.post(f'/survey/{token}/step/5', data={})

    assert response.status_code == 200
    assert b'Please select a position on the grid to continue.' in response.data

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert 'profile_grid' not in submission.answers
    assert submission.persona_id is None


def test_grid_step_with_a_valid_cell_advances(client, db):
    token = _start_new(client)
    _answer_up_to_grid(client, token)
    response = client.post(f'/survey/{token}/step/5', data={'profile_grid': '0,0'})  # -> accountant

    assert response.status_code == 302
    assert response.headers['Location'].endswith(f'/survey/{token}/result')

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.answers['profile_grid'] == [0, 0]
    assert submission.persona_id == 'accountant'


# ---------------------------------------------------------------------------
# multi_exact — exact count required
# ---------------------------------------------------------------------------

def test_multi_exact_wrong_count_rerenders_without_advancing(client, db):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'respondent_type': str(INDIVIDUAL)})
    client.post(f'/survey/{token}/step/2', data={'q_worded': '0'})
    client.post(f'/survey/{token}/step/3', data={'q_triangle': '0'})
    response = client.post(f'/survey/{token}/step/4', data={'q_multi_exact': ['0']})  # only 1, needs 2

    assert response.status_code == 200
    assert b'Please select exactly 2 options.' in response.data

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert 'q_multi_exact' not in submission.answers


def test_multi_exact_exact_count_advances_and_persists(client, db):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'respondent_type': str(INDIVIDUAL)})
    client.post(f'/survey/{token}/step/2', data={'q_worded': '0'})
    client.post(f'/survey/{token}/step/3', data={'q_triangle': '0'})
    response = client.post(f'/survey/{token}/step/4', data={'q_multi_exact': ['1', '3']})

    assert response.status_code == 302
    assert response.headers['Location'].endswith(f'/survey/{token}/step/5')

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert sorted(submission.answers['q_multi_exact']) == [1, 3]


# ---------------------------------------------------------------------------
# triangle
# ---------------------------------------------------------------------------

def test_triangle_step_persists_a_single_int_and_advances(client, db):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'respondent_type': str(INDIVIDUAL)})
    client.post(f'/survey/{token}/step/2', data={'q_worded': '0'})
    response = client.post(f'/survey/{token}/step/3', data={'q_triangle': '2'})

    assert response.status_code == 302
    assert response.headers['Location'].endswith(f'/survey/{token}/step/4')

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.answers['q_triangle'] == 2


def test_triangle_widget_renders_all_three_corner_options(client):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'respondent_type': str(INDIVIDUAL)})
    client.post(f'/survey/{token}/step/2', data={'q_worded': '0'})
    response = client.get(f'/survey/{token}/step/3')

    assert response.status_code == 200
    assert b'Corner A' in response.data
    assert b'Corner B' in response.data
    assert b'Corner C' in response.data


# ---------------------------------------------------------------------------
# Per-audience option wording
# ---------------------------------------------------------------------------

def test_organisation_track_shows_the_organisation_wording(client):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'respondent_type': str(ORGANISATION)})
    response = client.get(f'/survey/{token}/step/2')

    assert response.status_code == 200
    assert b'We want our own answer' in response.data
    assert b'I want my own answer' not in response.data


def test_individual_track_shows_the_default_wording(client):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'respondent_type': str(INDIVIDUAL)})
    response = client.get(f'/survey/{token}/step/2')

    assert response.status_code == 200
    assert b'I want my own answer' in response.data
    assert b'We want our own answer' not in response.data


def test_before_routing_the_default_wording_is_used(client):
    """Defensive/edge case only — in normal flow the router is step 1, so
    this exercises the un-routed fallback directly (audience is None)."""
    token = _start_new(client)
    response = client.get(f'/survey/{token}/step/1')
    assert response.status_code == 200
    # step 1 is the router itself; confirm no crash and normal rendering.
    assert b'individual' in response.data.lower()


# ---------------------------------------------------------------------------
# Result page
# ---------------------------------------------------------------------------

def test_result_page_renders_the_labelled_grid_with_chosen_persona(client, db):
    token = _start_new(client)
    _answer_up_to_grid(client, token)
    client.post(f'/survey/{token}/step/5', data={'profile_grid': '2,0'})  # -> activist

    response = client.get(f'/survey/{token}/result')
    assert response.status_code == 200
    assert b'Your position on the grid' in response.data
    assert b'The Activist' in response.data
    assert b'grid-cell--selected' in response.data


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------

def test_security_headers_present_on_grid_step(client):
    token = _start_new(client)
    _answer_up_to_grid(client, token)
    response = client.get(f'/survey/{token}/step/5')

    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['X-Content-Type-Options'] == 'nosniff'


def test_security_headers_present_on_result_page(client):
    token = _start_new(client)
    _answer_up_to_grid(client, token)
    client.post(f'/survey/{token}/step/5', data={'profile_grid': '0,0'})

    response = client.get(f'/survey/{token}/result')
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
