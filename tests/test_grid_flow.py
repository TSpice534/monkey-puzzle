"""Route tests for the new question types added for backlog #0003: the
interactive persona grid (mandatory to advance, grid-direct classification),
`triangle`, `multi_exact`, and per-audience option wording. Also covers
`multi_range` (backlog #0014: choose-a-range, not exactly-N). Uses
tests/fixtures/survey_grid.yaml (6 steps: respondent_type, q_worded,
q_triangle, q_multi_exact, profile_grid, q_multi_range)."""
import os

import pytest

from app.models import Submission
from app.survey.loader import clear_survey_cache
from app.survey.routes import _read_answer

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


def _answer_up_to_multi_range(client, token, audience=INDIVIDUAL, worded_index=0):
    """POST steps 1-5 (router, q_worded, q_triangle, q_multi_exact,
    profile_grid), leaving step 6 (q_multi_range) unanswered."""
    _answer_up_to_grid(client, token, audience=audience, worded_index=worded_index)
    client.post(f'/survey/{token}/step/5', data={'profile_grid': '1,1'})


def _input_tag(body, input_id):
    """The full `<input ...>` tag whose `id="{input_id}"` attribute matches
    exactly (no accidental prefix match, e.g. `q_multi_range_0` vs
    `q_multi_range_0_extra`) — mirrors the helper of the same name in
    test_real_survey_e2e.py, used here to check a checkbox's `checked` state
    in isolation from its siblings."""
    marker = f'id="{input_id}"'
    marker_start = body.index(marker)
    tag_start = body.rindex('<input', 0, marker_start)
    tag_end = body.index('>', marker_start)
    return body[tag_start:tag_end]


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
    client.post(f'/survey/{token}/step/5', data={'profile_grid': '1,1'})  # -> entrepreneur
    final = client.post(f'/survey/{token}/step/6', data={'q_multi_range': ['0']})

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
    assert response.headers['Location'].endswith(f'/survey/{token}/step/6')

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.answers['profile_grid'] == [0, 0]
    assert submission.persona_id is None  # not yet classified — q_multi_range still pending


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
# multi_range — choose_min/choose_max range required (backlog #0014)
# ---------------------------------------------------------------------------

def test_multi_range_too_few_rerenders_without_advancing(client, db):
    token = _start_new(client)
    _answer_up_to_multi_range(client, token)
    response = client.post(f'/survey/{token}/step/6', data={})  # 0 selections, needs 1-3

    assert response.status_code == 200
    assert b'Please select between 1 and 3 options.' in response.data

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert 'q_multi_range' not in submission.answers


def test_multi_range_too_many_rerenders_without_advancing(client, db):
    token = _start_new(client)
    _answer_up_to_multi_range(client, token)
    response = client.post(
        f'/survey/{token}/step/6',
        data={'q_multi_range': ['0', '1', '2', '3']},  # 4 selections, needs 1-3
    )

    assert response.status_code == 200
    assert b'Please select between 1 and 3 options.' in response.data

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert 'q_multi_range' not in submission.answers


def test_multi_range_valid_count_advances_and_persists(client, db):
    token = _start_new(client)
    _answer_up_to_multi_range(client, token)
    response = client.post(f'/survey/{token}/step/6', data={'q_multi_range': ['2', '0']})

    assert response.status_code == 302

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert sorted(submission.answers['q_multi_range']) == [0, 2]


def test_multi_range_step_renders_instructions_line(client):
    token = _start_new(client)
    _answer_up_to_multi_range(client, token)
    response = client.get(f'/survey/{token}/step/6')

    assert response.status_code == 200
    assert b'Choose up to 3 options.' in response.data


def test_multi_range_too_many_rerender_keeps_the_partial_selection_checked(client):
    """Edge case named explicitly in the spec: on a failed submit,
    `saved_value` round-trips into the rerender so the respondent doesn't
    lose their partial selection — same mechanism as `multi_exact`."""
    token = _start_new(client)
    _answer_up_to_multi_range(client, token)
    response = client.post(
        f'/survey/{token}/step/6',
        data={'q_multi_range': ['0', '1', '2', '3']},  # 4 selections, over choose_max
    )
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    for checked_id in ('q_multi_range_0', 'q_multi_range_1', 'q_multi_range_2', 'q_multi_range_3'):
        assert 'checked' in _input_tag(body, checked_id)


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


def test_read_answer_maps_triangle_comma_pair_to_edge_list_and_single_int_to_corner():
    """backlog #0010: _read_answer's triangle branch — 'i,j' parses to a
    2-int list (edge pick), a bare index still parses to a single int
    (corner pick, regression-guard)."""
    question = {'id': 'q_triangle', 'type': 'triangle'}
    assert _read_answer(question, {'q_triangle': '0,1'}) == [0, 1]
    assert _read_answer(question, {'q_triangle': '0'}) == 0


@pytest.mark.parametrize('raw', ['a,b', '0,1,2', '0,', ',', '', '0,a', 'a,1'])
def test_read_answer_triangle_malformed_pair_returns_none(raw):
    """backlog #0010: malformed 'i,j' input (non-numeric parts, wrong part
    count, empty/missing parts) must not raise — it falls through to None,
    same as an untouched question, not an exception."""
    question = {'id': 'q_triangle', 'type': 'triangle'}
    assert _read_answer(question, {'q_triangle': raw}) is None


def test_read_answer_triangle_returns_none_when_field_absent_from_form():
    """The question was never posted at all (e.g. a skipped optional
    triangle step) — `form.get(qid)` is None, short-circuiting before either
    parse attempt."""
    question = {'id': 'q_triangle', 'type': 'triangle'}
    assert _read_answer(question, {}) is None


def test_read_answer_triangle_duplicate_index_pair_still_parses():
    """`_read_answer` only parses shape ('i,j' -> [i, j]); it does not
    validate that the pair is a real adjacent-corner edge. A duplicate
    index like '1,1' parses to [1, 1] — garbage-in defensive handling for
    a bogus/duplicate edge lives downstream in `resolve_now_next`'s
    `options_by_index.get` lookup (covered in tests/test_persona.py)."""
    question = {'id': 'q_triangle', 'type': 'triangle'}
    assert _read_answer(question, {'q_triangle': '1,1'}) == [1, 1]


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
    client.post(f'/survey/{token}/step/6', data={'q_multi_range': ['0']})

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
    client.post(f'/survey/{token}/step/6', data={'q_multi_range': ['0']})

    response = client.get(f'/survey/{token}/result')
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
