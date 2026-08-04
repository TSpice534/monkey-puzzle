"""Respondent-type routing: the first question ('individual' or
'organisation') sets `Submission.audience`, which determines which
audience-tagged questions appear for the rest of the survey. Uses
tests/fixtures/survey_audience.yaml, which deliberately gives the two
tracks different lengths (organisation: 5 steps, individual: 4 steps) so
these tests exercise `total` actually changing, not just question content."""
import os

import pytest

from app.models import Submission
from app.survey.loader import clear_survey_cache

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'survey_audience.yaml')

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
    return response.headers['Location'].split('/survey/')[1].split('/step/')[0]


# ---------------------------------------------------------------------------
# The router question itself
# ---------------------------------------------------------------------------

def test_step_one_is_the_router_question(client):
    token = _start_new(client)
    response = client.get(f'/survey/{token}/step/1')
    assert response.status_code == 200
    assert b'Individual or organisation?' in response.data


def test_answering_router_sets_submission_audience(client, db):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'respondent_type': str(ORGANISATION)})
    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.audience == 'organisation'
    assert submission.answers['respondent_type'] == ORGANISATION


def test_router_answer_is_stored_like_any_other_answer(client, db):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'respondent_type': str(INDIVIDUAL)})
    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.audience == 'individual'


# ---------------------------------------------------------------------------
# Before routing: only shared questions are reachable
# ---------------------------------------------------------------------------

def test_before_answering_router_only_shared_questions_are_reachable(client):
    """audience is None until step 1 is answered — effective list is just
    the router plus the two untagged (shared) questions: [respondent_type,
    q_shared, q_short_text] = 3 steps. Step 4 (an audience-gated question)
    is unreachable and 404s."""
    token = _start_new(client)
    response = client.get(f'/survey/{token}/step/2')
    assert response.status_code == 200
    assert b'Shared question' in response.data

    response = client.get(f'/survey/{token}/step/3')
    assert response.status_code == 200
    assert b'Anything else?' in response.data

    response = client.get(f'/survey/{token}/step/4')
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Organisation track
# ---------------------------------------------------------------------------

def test_organisation_track_shows_organisation_only_questions(client):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'respondent_type': str(ORGANISATION)})
    client.post(f'/survey/{token}/step/2', data={'q_shared': '0'})

    response = client.get(f'/survey/{token}/step/3')
    assert response.status_code == 200
    assert b'Organisation-only question 1' in response.data


def test_organisation_track_does_not_show_individual_only_question(client):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'respondent_type': str(ORGANISATION)})
    client.post(f'/survey/{token}/step/2', data={'q_shared': '0'})
    client.post(f'/survey/{token}/step/3', data={'q_org_1': '0'})
    response = client.post(f'/survey/{token}/step/4', data={'q_org_2': '0'})
    # Step 5 (the last, org track) is the shared short_text question, not
    # the individual-only question — confirm by finishing the flow cleanly.
    assert response.status_code == 302
    assert response.headers['Location'].endswith(f'/survey/{token}/step/5')

    response = client.get(f'/survey/{token}/step/5')
    assert b'Anything else?' in response.data


def test_organisation_track_completes_with_five_steps(client, db):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'respondent_type': str(ORGANISATION)})  # entrepreneur/cooperator: 0
    client.post(f'/survey/{token}/step/2', data={'q_shared': '0'})       # inventor: 2
    client.post(f'/survey/{token}/step/3', data={'q_org_1': '0'})        # implementer: 1
    client.post(f'/survey/{token}/step/4', data={'q_org_2': '0'})        # architect: 1
    final = client.post(f'/survey/{token}/step/5', data={'q_short_text': 'done'})

    assert final.status_code == 302
    assert final.headers['Location'].endswith(f'/survey/{token}/result')

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.persona_id == 'inventor'
    assert submission.audience == 'organisation'


# ---------------------------------------------------------------------------
# Individual track
# ---------------------------------------------------------------------------

def test_individual_track_shows_individual_only_question(client):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'respondent_type': str(INDIVIDUAL)})
    client.post(f'/survey/{token}/step/2', data={'q_shared': '0'})

    response = client.get(f'/survey/{token}/step/3')
    assert response.status_code == 200
    assert b'Individual-only question 1' in response.data


def test_individual_track_completes_with_four_steps(client, db):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'respondent_type': str(INDIVIDUAL)})
    client.post(f'/survey/{token}/step/2', data={'q_shared': '1'})   # accountant: 2
    client.post(f'/survey/{token}/step/3', data={'q_ind_1': '1'})    # cooperator: 1
    final = client.post(f'/survey/{token}/step/4', data={'q_short_text': 'done'})

    assert final.status_code == 302
    assert final.headers['Location'].endswith(f'/survey/{token}/result')

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.persona_id == 'accountant'
    assert submission.audience == 'individual'


def test_individual_track_step_five_404s_it_only_has_four_steps(client):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'respondent_type': str(INDIVIDUAL)})
    response = client.get(f'/survey/{token}/step/5')
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Switching audience mid-flow
# ---------------------------------------------------------------------------

def test_switching_audience_changes_the_rest_of_the_flow(client, db):
    """Answer the router as organisation, proceed a step, then go back to
    step 1 and switch to individual — the questions from that point on
    should reflect the new choice, not the old one."""
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'respondent_type': str(ORGANISATION)})
    client.post(f'/survey/{token}/step/2', data={'q_shared': '0'})

    # Switch tracks.
    client.post(f'/survey/{token}/step/1', data={'respondent_type': str(INDIVIDUAL)})

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.audience == 'individual'

    response = client.get(f'/survey/{token}/step/3')
    assert b'Individual-only question 1' in response.data


# ---------------------------------------------------------------------------
# result — redirect-into-flow uses the effective (audience-filtered) list
# ---------------------------------------------------------------------------

def test_result_before_completion_redirects_using_effective_questions(client):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'respondent_type': str(INDIVIDUAL)})
    client.post(f'/survey/{token}/step/2', data={'q_shared': '0'})

    response = client.get(f'/survey/{token}/result')
    assert response.status_code == 302
    # Next unanswered question for the individual track is step 3.
    assert response.headers['Location'].endswith(f'/survey/{token}/step/3')
