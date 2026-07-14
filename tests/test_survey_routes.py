"""Survey flow routes: start/step/result, using the small fixture survey
(tests/fixtures/survey_min.yaml) so a full run is a handful of requests."""
import os

import pytest

from app.models import Submission
from app.survey.loader import clear_survey_cache, load_survey

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'survey_min.yaml')

PERSONA_IDS = [
    'documenter', 'implementer', 'developer', 'advocate', 'communicator',
    'activist', 'connector', 'cooperator', 'entrepreneur',
]


@pytest.fixture(autouse=True)
def _use_fixture_survey(app):
    """Point every test in this module at the small fixture survey instead
    of the real placeholder content, and reset the loader's cache so the
    swap actually takes effect."""
    app.config['SURVEY_PATH'] = FIXTURE_PATH
    clear_survey_cache()
    yield
    clear_survey_cache()


def _start_new(client):
    response = client.get('/survey/start')
    assert response.status_code == 302
    # Location: /survey/<token>/step/1
    return response.headers['Location'].split('/survey/')[1].split('/step/')[0]


# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------

def test_start_creates_a_submission_and_redirects_to_step_one(client, db):
    response = client.get('/survey/start')
    assert response.status_code == 302

    submission = db.session.query(Submission).one()
    assert response.headers['Location'].endswith(f'/survey/{submission.token}/step/1')
    assert submission.answers == {}
    assert submission.persona_id is None


# ---------------------------------------------------------------------------
# step — GET
# ---------------------------------------------------------------------------

def test_step_get_renders_the_question_prompt(client):
    token = _start_new(client)
    response = client.get(f'/survey/{token}/step/1')
    assert response.status_code == 200
    assert b'Pick one' in response.data


def test_step_get_prefills_saved_answer(client):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'q_single': '0'})
    response = client.get(f'/survey/{token}/step/1', follow_redirects=False)
    # Revisiting step 1 directly (not via redirect) should show the saved
    # choice pre-checked.
    body = response.get_data(as_text=True)
    assert 'checked' in body


def test_unknown_token_404s_on_step(client):
    response = client.get('/survey/not-a-real-token/step/1')
    assert response.status_code == 404


def test_step_zero_404s(client):
    token = _start_new(client)
    response = client.get(f'/survey/{token}/step/0')
    assert response.status_code == 404


def test_step_beyond_total_404s(client):
    token = _start_new(client)
    response = client.get(f'/survey/{token}/step/99')
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# step — POST
# ---------------------------------------------------------------------------

def test_step_post_persists_answer_under_question_id(client, db):
    token = _start_new(client)
    response = client.post(f'/survey/{token}/step/1', data={'q_single': '0'})
    assert response.status_code == 302
    assert response.headers['Location'].endswith(f'/survey/{token}/step/2')

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.answers['q_single'] == 0


def test_step_post_multi_with_no_selection_stores_empty_list(client, db):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'q_single': '0'})
    client.post(f'/survey/{token}/step/2', data={})
    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.answers['q_multi'] == []


def test_step_post_short_text_is_trimmed(client, db):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'q_single': '0'})
    client.post(f'/survey/{token}/step/2', data={'q_multi': ['0']})
    client.post(f'/survey/{token}/step/3', data={'q_spectrum': '1'})
    client.post(f'/survey/{token}/step/4', data={'q_short_text': '  hello world  '})
    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.answers['q_short_text'] == 'hello world'


def test_completing_final_step_sets_persona_and_score_vector(client, db):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'q_single': '0'})       # developer: 2
    client.post(f'/survey/{token}/step/2', data={'q_multi': ['0', '1']})  # implementer:1, communicator:1
    client.post(f'/survey/{token}/step/3', data={'q_spectrum': '1'})     # entrepreneur: 1
    final_response = client.post(f'/survey/{token}/step/4', data={'q_short_text': 'because reasons'})

    assert final_response.status_code == 302
    assert final_response.headers['Location'].endswith(f'/survey/{token}/result')

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.persona_id == 'developer'
    assert set(submission.score_vector.keys()) == set(PERSONA_IDS)


def test_result_page_renders_persona_name_after_completion(client):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'q_single': '0'})
    client.post(f'/survey/{token}/step/2', data={'q_multi': []})
    client.post(f'/survey/{token}/step/3', data={'q_spectrum': '0'})
    client.post(f'/survey/{token}/step/4', data={'q_short_text': ''})

    survey = load_survey(FIXTURE_PATH)
    persona_name = survey['personas']['developer']['name']

    response = client.get(f'/survey/{token}/result')
    assert response.status_code == 200
    assert persona_name.encode() in response.data


def test_answers_accumulate_across_all_steps(client, db):
    """Each step's answer must still be present after later steps are
    submitted — submission.answers is a running accumulation, not just the
    most recently posted question."""
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'q_single': '0'})
    client.post(f'/survey/{token}/step/2', data={'q_multi': ['1']})
    client.post(f'/survey/{token}/step/3', data={'q_spectrum': '1'})

    submission = db.session.query(Submission).filter_by(token=token).one()
    # Only 3 of 4 questions answered so far; all three must still be present
    # (not overwritten/dropped by the later posts).
    assert submission.answers == {
        'q_single': 0,
        'q_multi': [1],
        'q_spectrum': 1,
    }


# ---------------------------------------------------------------------------
# Resubmitting a completed survey
# ---------------------------------------------------------------------------

def test_resubmitting_final_step_reclassifies_with_new_answer(client, db):
    """A submission that has already been classified can be revisited and
    re-completed (e.g. the user goes Back and changes an answer, then
    re-submits the final step) — the persona/score_vector must reflect the
    *new* answers, not silently keep the stale classification."""
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'q_single': '0'})       # developer: 2
    client.post(f'/survey/{token}/step/2', data={'q_multi': []})
    client.post(f'/survey/{token}/step/3', data={'q_spectrum': '0'})
    client.post(f'/survey/{token}/step/4', data={'q_short_text': ''})

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.persona_id == 'developer'

    # Go back to step 1 and pick the other option, then re-complete.
    client.post(f'/survey/{token}/step/1', data={'q_single': '1'})       # documenter: 2
    client.post(f'/survey/{token}/step/2', data={'q_multi': []})
    client.post(f'/survey/{token}/step/3', data={'q_spectrum': '0'})
    final_response = client.post(f'/survey/{token}/step/4', data={'q_short_text': ''})

    assert final_response.status_code == 302
    assert final_response.headers['Location'].endswith(f'/survey/{token}/result')

    db.session.refresh(submission)
    assert submission.persona_id == 'documenter'
    assert submission.answers['q_single'] == 1


def test_editing_earlier_step_after_completion_does_not_retroactively_update_result(client, db):
    """Changing an earlier answer without re-submitting the final step
    leaves the previously-computed persona/score_vector untouched — the
    result page is only recomputed when the final step is (re)submitted,
    documenting the actual persist-then-classify behaviour."""
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'q_single': '0'})       # developer: 2
    client.post(f'/survey/{token}/step/2', data={'q_multi': []})
    client.post(f'/survey/{token}/step/3', data={'q_spectrum': '0'})
    client.post(f'/survey/{token}/step/4', data={'q_short_text': ''})

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.persona_id == 'developer'

    # Revisit step 1 and change the answer, but stop there (no re-submission
    # of the final step).
    client.post(f'/survey/{token}/step/1', data={'q_single': '1'})

    db.session.refresh(submission)
    assert submission.answers['q_single'] == 1
    assert submission.persona_id == 'developer'  # unchanged until re-completed

    response = client.get(f'/survey/{token}/result')
    assert response.status_code == 200  # already classified, so no redirect


def test_get_step_after_completion_still_renders(client):
    """Revisiting an already-answered step of a completed submission (e.g.
    via Back) still renders normally rather than erroring."""
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'q_single': '0'})
    client.post(f'/survey/{token}/step/2', data={'q_multi': []})
    client.post(f'/survey/{token}/step/3', data={'q_spectrum': '0'})
    client.post(f'/survey/{token}/step/4', data={'q_short_text': ''})

    response = client.get(f'/survey/{token}/step/1')
    assert response.status_code == 200
    assert 'checked' in response.get_data(as_text=True)


# ---------------------------------------------------------------------------
# result — edge cases
# ---------------------------------------------------------------------------

def test_result_before_completion_redirects_into_the_flow(client):
    token = _start_new(client)
    response = client.get(f'/survey/{token}/result')
    assert response.status_code == 302
    assert response.headers['Location'].endswith(f'/survey/{token}/step/1')


def test_result_redirects_to_first_unanswered_step(client):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'q_single': '0'})
    response = client.get(f'/survey/{token}/result')
    assert response.status_code == 302
    assert response.headers['Location'].endswith(f'/survey/{token}/step/2')


def test_unknown_token_404s_on_result(client):
    response = client.get('/survey/not-a-real-token/result')
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------

def test_security_headers_present_on_survey_step_page(client):
    token = _start_new(client)
    response = client.get(f'/survey/{token}/step/1')
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert 'Content-Security-Policy' in response.headers


def test_security_headers_present_on_result_page(client):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'q_single': '0'})
    client.post(f'/survey/{token}/step/2', data={'q_multi': []})
    client.post(f'/survey/{token}/step/3', data={'q_spectrum': '0'})
    client.post(f'/survey/{token}/step/4', data={'q_short_text': ''})

    response = client.get(f'/survey/{token}/result')
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert 'Content-Security-Policy' in response.headers
