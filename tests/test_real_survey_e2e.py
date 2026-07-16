"""Independent end-to-end verification of backlog #0003 against the REAL
content/survey.yaml (not a small fixture) — walks the full 11-step flow via
the Flask test client, exactly as a browser would, and checks the specific
risk areas flagged for this change: the grid's mandatory block-advance
behaviour, `multi_exact` exact-count validation, audience-aware wording
(including before the router is answered), and that the existing
radar/fingerprint chart plus the PDF/share/email routes still work against
the new 11-question content shape.

Every other test module in this suite drives a small fixture survey
(survey_min.yaml / survey_grid.yaml / survey_audience.yaml) through these
same routes. Nothing else in the suite walks content/survey.yaml itself
through the HTTP layer end-to-end (test_loader.py loads it directly;
test_persona.py calls classify_submission directly) — this module closes
that gap.
"""
import html as html_lib
import json
import os
import re

import pytest

from app.models import Submission
from app.survey.loader import clear_survey_cache

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_SURVEY_PATH = os.path.join(REPO_ROOT, 'content', 'survey.yaml')

PNG_MAGIC = b'\x89PNG\r\n\x1a\n'

INDIVIDUAL = 0
ORGANISATION = 1

# Step numbers for the real 11-question survey, per docs/SURVEY-TEMPLATE.md
# and content/survey.yaml (both audience tracks see all 11 — no `audience`
# tags are used in the real survey, per the coder's changes.md).
STEP_RESPONDENT_TYPE = 1
STEP_WHY_REASON = 2
STEP_MOTIVATION = 3
STEP_AMBITION = 4
STEP_SPACE_TO_PROGRESS = 5
STEP_NEED_MOST = 6
STEP_HAVE_ENOUGH = 7
STEP_PROFILE_GRID = 8
STEP_TOPICS = 9
STEP_SUPPORT_TYPE = 10
STEP_TARGET_GROUPS = 11
TOTAL_STEPS = 11


@pytest.fixture(autouse=True)
def _use_real_survey(app):
    # This is already Config's default (SURVEY_PATH points at
    # content/survey.yaml), but set + clear the cache explicitly so this
    # module is correct regardless of what ran before it.
    app.config['SURVEY_PATH'] = REAL_SURVEY_PATH
    clear_survey_cache()
    yield
    clear_survey_cache()


def _start_new(client):
    response = client.get('/survey/start')
    assert response.status_code == 302
    return response.headers['Location'].split('/survey/')[1].split('/step/')[0]


def _data_labels_json(body, question_id):
    """Parse the JSON payload of a spectrum question's `data-labels`
    attribute out of a rendered step page's HTML body."""
    marker = f'id="{question_id}_range"'
    tag_start = body.index(marker)
    tag_end = body.index('>', tag_start)
    tag = body[tag_start:tag_end]
    start = tag.index("data-labels='") + len("data-labels='")
    end = tag.index("'", start)
    return json.loads(tag[start:end])


def _current_label_text(body, question_id):
    """The live-label span's text, HTML-unescaped — i.e. what a browser
    actually displays. Normal single HTML-entity escaping in this SSR
    context (e.g. an apostrophe rendered as `&#39;` in the HTML source) is
    expected and correctly decoded by the browser; it is not the #0008
    double-escaping bug, which only affects the JS-consumed data-labels
    JSON attribute (checked separately via `_data_labels_json`)."""
    match = re.search(
        rf'<span id="{question_id}_current_label">(.*?)</span>', body, re.DOTALL
    )
    assert match, 'current label span not found in rendered page'
    return html_lib.unescape(match.group(1))


def _input_tag(body, input_id):
    """The full `<input ...>` tag whose `id="{input_id}"` attribute matches
    exactly (no accidental prefix match against e.g. `need_most_0_1` when
    looking up `need_most_0`) — used to check a specific radio's `checked`
    state in isolation from its siblings."""
    marker = f'id="{input_id}"'
    marker_start = body.index(marker)
    tag_start = body.rindex('<input', 0, marker_start)
    tag_end = body.index('>', marker_start)
    return body[tag_start:tag_end]


def _answer_up_to_grid(client, token, audience_index):
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(audience_index)})
    client.post(f'/survey/{token}/step/{STEP_WHY_REASON}', data={'why_reason': 'Because it matters.'})
    client.post(f'/survey/{token}/step/{STEP_MOTIVATION}', data={'motivation': '0'})
    client.post(f'/survey/{token}/step/{STEP_AMBITION}', data={'ambition': '0'})
    client.post(f'/survey/{token}/step/{STEP_SPACE_TO_PROGRESS}', data={'space_to_progress': '0'})
    client.post(f'/survey/{token}/step/{STEP_NEED_MOST}', data={'need_most': '0'})
    client.post(f'/survey/{token}/step/{STEP_HAVE_ENOUGH}', data={'have_enough': '0'})


def _complete_survey(client, audience_index=INDIVIDUAL, grid='1,1'):
    """Walk all 11 real-survey steps to completion. grid='1,1' -> entrepreneur."""
    token = _start_new(client)
    _answer_up_to_grid(client, token, audience_index)
    client.post(f'/survey/{token}/step/{STEP_PROFILE_GRID}', data={'profile_grid': grid})
    client.post(f'/survey/{token}/step/{STEP_TOPICS}', data={'topics': ['0', '1', '2']})
    client.post(f'/survey/{token}/step/{STEP_SUPPORT_TYPE}', data={'support_type': '0'})
    final = client.post(f'/survey/{token}/step/{STEP_TARGET_GROUPS}', data={'target_groups': '0'})
    return token, final


# ---------------------------------------------------------------------------
# Happy path — full 11-step flow, both audience tracks
# ---------------------------------------------------------------------------

def test_full_11_step_flow_individual_completes_and_classifies_via_grid(client, db):
    token, final = _complete_survey(client, audience_index=INDIVIDUAL, grid='1,1')  # -> entrepreneur

    assert final.status_code == 302
    assert final.headers['Location'].endswith(f'/survey/{token}/result')

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.persona_id == 'entrepreneur'
    assert submission.audience == 'individual'
    # Grid-direct resolution yields a one-hot vector (per persona.py).
    assert submission.score_vector['entrepreneur'] == 1.0
    assert all(v == 0.0 for pid, v in submission.score_vector.items() if pid != 'entrepreneur')
    assert set(submission.score_vector.keys()) == {
        'accountant', 'implementer', 'developer', 'advocate', 'communicator',
        'activist', 'connector', 'cooperator', 'entrepreneur',
    }
    # Innovation-curve result (backlog #0002): motivation/ambition/space_to_progress
    # all answered index 0 (score 1 each) -> sum 3; entrepreneur modifier +2 -> 5
    # -> Late Majority (band 3-7).
    assert submission.innovation_score == 5
    assert submission.innovation_band == 'Late Majority'


def test_full_11_step_flow_organisation_completes_and_classifies_via_grid(client, db):
    token, final = _complete_survey(client, audience_index=ORGANISATION, grid='0,0')  # -> accountant

    assert final.status_code == 302
    assert final.headers['Location'].endswith(f'/survey/{token}/result')

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.persona_id == 'accountant'
    assert submission.audience == 'organisation'
    # accountant's persona modifier is 0, so the total is just the raw
    # question-score sum (3) -> Late Majority (band 3-7).
    assert submission.innovation_score == 3
    assert submission.innovation_band == 'Late Majority'


def test_all_nine_grid_cells_resolve_to_the_documented_persona_end_to_end(client, db):
    """Cross-check the confirmed grid mapping table in the spec end-to-end
    through the real route flow (not just the classifier unit test)."""
    expected = {
        (0, 2): 'developer', (1, 2): 'advocate', (2, 2): 'cooperator',
        (0, 1): 'implementer', (1, 1): 'entrepreneur', (2, 1): 'connector',
        (0, 0): 'accountant', (1, 0): 'communicator', (2, 0): 'activist',
    }
    for (x, y), persona_id in expected.items():
        token, final = _complete_survey(client, audience_index=INDIVIDUAL, grid=f'{x},{y}')
        assert final.status_code == 302
        submission = db.session.query(Submission).filter_by(token=token).one()
        assert submission.persona_id == persona_id, f'cell ({x},{y}) expected {persona_id}'


# ---------------------------------------------------------------------------
# Innovation-curve scoring + banding (backlog #0002) — a worked high-score
# example (all sliders at index 4/2/2, developer's +4 modifier) end-to-end.
# ---------------------------------------------------------------------------

def test_high_scoring_answers_and_developer_modifier_classify_as_innovators(client, db):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
    client.post(f'/survey/{token}/step/{STEP_WHY_REASON}', data={'why_reason': 'Because it matters.'})
    client.post(f'/survey/{token}/step/{STEP_MOTIVATION}', data={'motivation': '4'})
    client.post(f'/survey/{token}/step/{STEP_AMBITION}', data={'ambition': '2'})
    client.post(f'/survey/{token}/step/{STEP_SPACE_TO_PROGRESS}', data={'space_to_progress': '2'})
    client.post(f'/survey/{token}/step/{STEP_NEED_MOST}', data={'need_most': '0'})
    client.post(f'/survey/{token}/step/{STEP_HAVE_ENOUGH}', data={'have_enough': '0'})
    client.post(f'/survey/{token}/step/{STEP_PROFILE_GRID}', data={'profile_grid': '0,2'})  # -> developer
    client.post(f'/survey/{token}/step/{STEP_TOPICS}', data={'topics': ['0', '1', '2']})
    client.post(f'/survey/{token}/step/{STEP_SUPPORT_TYPE}', data={'support_type': '0'})
    final = client.post(f'/survey/{token}/step/{STEP_TARGET_GROUPS}', data={'target_groups': '0'})

    assert final.status_code == 302
    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.persona_id == 'developer'
    assert submission.innovation_score == 19
    assert submission.innovation_band == 'Innovators'


# ---------------------------------------------------------------------------
# Grid — mandatory to advance (step 8 of the real survey)
# ---------------------------------------------------------------------------

def test_grid_step_cannot_be_skipped_on_the_real_survey(client, db):
    token = _start_new(client)
    _answer_up_to_grid(client, token, INDIVIDUAL)

    response = client.post(f'/survey/{token}/step/{STEP_PROFILE_GRID}', data={})

    assert response.status_code == 200
    assert b'Please select a position on the grid to continue.' in response.data

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert 'profile_grid' not in submission.answers
    assert submission.persona_id is None


def test_grid_step_get_after_failed_advance_still_shows_step_eight(client):
    """A no-selection POST must not silently advance — GETing the same step
    afterwards should still be the grid, not step 9."""
    token = _start_new(client)
    _answer_up_to_grid(client, token, INDIVIDUAL)
    client.post(f'/survey/{token}/step/{STEP_PROFILE_GRID}', data={})

    response = client.get(f'/survey/{token}/step/{STEP_PROFILE_GRID}')
    assert response.status_code == 200
    assert b'Where would you like to act, and how?' in response.data


# ---------------------------------------------------------------------------
# multi_exact — exact-count validation (step 9, `topics`, choose_exactly: 3)
# ---------------------------------------------------------------------------

def test_topics_wrong_count_rerenders_without_advancing(client, db):
    token = _start_new(client)
    _answer_up_to_grid(client, token, INDIVIDUAL)
    client.post(f'/survey/{token}/step/{STEP_PROFILE_GRID}', data={'profile_grid': '1,1'})

    response = client.post(f'/survey/{token}/step/{STEP_TOPICS}', data={'topics': ['0', '1']})  # only 2, needs 3

    assert response.status_code == 200
    assert b'Please select exactly 3 options.' in response.data

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert 'topics' not in submission.answers


def test_topics_too_many_also_rerenders_without_advancing(client, db):
    token = _start_new(client)
    _answer_up_to_grid(client, token, INDIVIDUAL)
    client.post(f'/survey/{token}/step/{STEP_PROFILE_GRID}', data={'profile_grid': '1,1'})

    response = client.post(f'/survey/{token}/step/{STEP_TOPICS}', data={'topics': ['0', '1', '2', '3']})  # 4, needs 3

    assert response.status_code == 200
    assert b'Please select exactly 3 options.' in response.data


def test_topics_exact_count_advances_and_persists(client, db):
    token = _start_new(client)
    _answer_up_to_grid(client, token, INDIVIDUAL)
    client.post(f'/survey/{token}/step/{STEP_PROFILE_GRID}', data={'profile_grid': '1,1'})

    response = client.post(f'/survey/{token}/step/{STEP_TOPICS}', data={'topics': ['2', '4', '7']})

    assert response.status_code == 302
    assert response.headers['Location'].endswith(f'/survey/{token}/step/{STEP_SUPPORT_TYPE}')

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert sorted(submission.answers['topics']) == [2, 4, 7]


# ---------------------------------------------------------------------------
# Per-audience wording — spectrum (motivation) and single (target_groups),
# including the un-routed (audience is None) fallback
# ---------------------------------------------------------------------------

def test_motivation_spectrum_shows_organisation_wording_on_the_org_track(client):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(ORGANISATION)})

    response = client.get(f'/survey/{token}/step/{STEP_MOTIVATION}')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'We feel we must act on this topic' in body
    assert 'I feel the need to act on this topic' not in body
    # The live-label JS reads this JSON — must also carry org wording.
    assert 'We feel we must act' in body


def test_motivation_spectrum_shows_individual_wording_on_the_individual_track(client):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})

    response = client.get(f'/survey/{token}/step/{STEP_MOTIVATION}')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'I feel the need to act on this topic' in body
    assert 'We feel we must act on this topic' not in body


def test_motivation_spectrum_defaults_to_individual_wording_before_routing(client):
    """Navigating straight to step 3 without having POSTed the router yet —
    audience is still None. Per spec this must fall back to the Individual
    (`label`) wording, not crash and not show organisation wording."""
    token = _start_new(client)
    response = client.get(f'/survey/{token}/step/{STEP_MOTIVATION}')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'I feel the need to act on this topic' in body
    assert 'We feel we must act on this topic' not in body


def test_target_groups_single_choice_wording_switches_by_audience(client):
    token_org = _start_new(client)
    client.post(f'/survey/{token_org}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(ORGANISATION)})
    org_body = client.get(f'/survey/{token_org}/step/{STEP_TARGET_GROUPS}').get_data(as_text=True)
    assert 'We want to engage our audience' in org_body
    assert 'I want to engage my audience' not in org_body

    token_ind = _start_new(client)
    client.post(f'/survey/{token_ind}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
    ind_body = client.get(f'/survey/{token_ind}/step/{STEP_TARGET_GROUPS}').get_data(as_text=True)
    assert 'I want to engage my audience' in ind_body
    assert 'We want to engage our audience' not in ind_body


def test_grid_instruction_copy_switches_by_audience(client):
    token_org = _start_new(client)
    client.post(f'/survey/{token_org}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(ORGANISATION)})
    _answer_up_to_grid(client, token_org, ORGANISATION)
    org_body = client.get(f'/survey/{token_org}/step/{STEP_PROFILE_GRID}').get_data(as_text=True)
    assert 'Find your organisation on this grid and select' in org_body

    token_ind = _start_new(client)
    _answer_up_to_grid(client, token_ind, INDIVIDUAL)
    ind_body = client.get(f'/survey/{token_ind}/step/{STEP_PROFILE_GRID}').get_data(as_text=True)
    assert 'Find yourself on this grid and select' in ind_body


# ---------------------------------------------------------------------------
# motivation — now a 5-position slider with 2 unlabelled between-stops
# (backlog #0002)
# ---------------------------------------------------------------------------

def test_motivation_slider_unlabelled_stop_label_text_is_not_rendered(client):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
    response = client.get(f'/survey/{token}/step/{STEP_MOTIVATION}')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'Intermediate position' not in body
    # The 3 labelled stops are still present.
    assert 'I feel the need to act on this topic' in body
    assert 'I understand I need to act on this topic' in body
    assert 'It is part of my role' in body


@pytest.mark.parametrize('index', [0, 1, 2, 3, 4])
def test_motivation_slider_accepts_all_five_positions(client, index):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
    response = client.post(f'/survey/{token}/step/{STEP_MOTIVATION}', data={'motivation': str(index)})
    assert response.status_code == 302


# ---------------------------------------------------------------------------
# backlog #0008 (apostrophe escaping) + #0009 (static row removal), against
# the real content/survey.yaml. `ambition` (step 4) is the only real
# question whose option wording contains apostrophes, e.g.
# "I want to make sure I'm keeping pace with those around me" (individual)
# and "We want to make sure we're keeping pace with those around us" (org).
# ---------------------------------------------------------------------------

APOSTROPHE_OPTION_INDEX = 3
APOSTROPHE_LABEL_INDIVIDUAL = "I want to make sure I'm keeping pace with those around me"
APOSTROPHE_LABEL_ORGANISATION = "We want to make sure we're keeping pace with those around us"


def test_ambition_apostrophe_option_renders_correctly_on_fresh_get(client):
    """#0008: on a fresh GET (no saved_value yet, current_index defaults to
    0), the data-labels JSON payload must carry the real apostrophe
    character for every option — not the double-escaped `&#39;` literal
    the old option_label()-via-Markup path produced."""
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
    response = client.get(f'/survey/{token}/step/{STEP_AMBITION}')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    labels = _data_labels_json(body, 'ambition')
    assert APOSTROPHE_LABEL_INDIVIDUAL in labels
    assert not any('&#39;' in label for label in labels)
    # value defaults to index 0 (no apostrophe option) — confirms the
    # fresh-GET initial-value path independently of the apostrophe fix.
    assert 'value="0"' in body


def test_ambition_apostrophe_option_renders_correctly_with_saved_value(client):
    """#0008 + initial-label-on-load: selecting the apostrophe-containing
    option, then GETting the step again (saved_value now set), must show
    the real apostrophe in both the live label and the data-labels JSON —
    not `&#39;`."""
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
    client.post(f'/survey/{token}/step/{STEP_AMBITION}', data={'ambition': str(APOSTROPHE_OPTION_INDEX)})

    response = client.get(f'/survey/{token}/step/{STEP_AMBITION}')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f'value="{APOSTROPHE_OPTION_INDEX}"' in body
    assert _current_label_text(body, 'ambition') == APOSTROPHE_LABEL_INDIVIDUAL
    # The JS-consumed JSON payload is where the #0008 double-escape bug
    # actually manifested (textContent doesn't decode HTML entities).
    labels = _data_labels_json(body, 'ambition')
    assert not any('&#39;' in label for label in labels)
    assert labels[APOSTROPHE_OPTION_INDEX] == APOSTROPHE_LABEL_INDIVIDUAL


def test_ambition_apostrophe_option_renders_correctly_on_organisation_track(client):
    """Audience-aware wording (label_organisation) combined with the
    apostrophe fix — both must hold together."""
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(ORGANISATION)})
    client.post(f'/survey/{token}/step/{STEP_AMBITION}', data={'ambition': str(APOSTROPHE_OPTION_INDEX)})

    response = client.get(f'/survey/{token}/step/{STEP_AMBITION}')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert _current_label_text(body, 'ambition') == APOSTROPHE_LABEL_ORGANISATION
    assert APOSTROPHE_LABEL_INDIVIDUAL not in body
    labels = _data_labels_json(body, 'ambition')
    assert not any('&#39;' in label for label in labels)
    assert labels[APOSTROPHE_OPTION_INDEX] == APOSTROPHE_LABEL_ORGANISATION


def test_motivation_static_label_row_is_gone_from_rendered_html(client):
    """#0009: the static row that used to print every option label under
    the slider is deleted — only the live label span remains. "It is part
    of my role" is motivation's last option (index 4), not the default
    selected one (index 0), so before #0009 it would appear twice: once
    inside the JS data-labels JSON attribute, and once again as static
    visible text in the now-deleted label row."""
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
    response = client.get(f'/survey/{token}/step/{STEP_MOTIVATION}')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert body.count('It is part of my role') == 1
    # The removed row's exact class combination (the progress bar reuses
    # the same classes plus an extra "mb-1", so this string is unique to
    # the deleted static row).
    assert 'class="d-flex justify-content-between small text-muted">' not in body


def test_motivation_current_label_is_empty_not_undefined_when_unlabelled_stop_selected(client):
    """Edge case: selecting one of motivation's two unlabelled between-stop
    positions must render an empty live label server-side, not a stray
    'undefined'/'None'/exception."""
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
    client.post(f'/survey/{token}/step/{STEP_MOTIVATION}', data={'motivation': '1'})  # unlabelled between-stop

    response = client.get(f'/survey/{token}/step/{STEP_MOTIVATION}')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '<span id="motivation_current_label"></span>' in body
    assert 'undefined' not in body


# ---------------------------------------------------------------------------
# Triangle widget renders correctly on the real content (need_most, step 6)
# ---------------------------------------------------------------------------

def test_triangle_question_renders_all_three_options_on_real_survey(client):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
    response = client.get(f'/survey/{token}/step/{STEP_NEED_MOST}')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'More capacity' in body
    assert 'More knowledge' in body
    assert 'More support' in body
    assert 'role="radiogroup"' in body


def test_triangle_question_renders_the_three_edge_nodes(client):
    """backlog #0010: 3 edge midpoint nodes render alongside the 3 corners,
    each labelled with both flanking corners' option_label joined by '&'."""
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
    response = client.get(f'/survey/{token}/step/{STEP_NEED_MOST}')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'value="0,1"' in body
    assert 'value="1,2"' in body
    assert 'value="0,2"' in body
    assert 'More capacity &amp; More knowledge' in body


def test_triangle_edge_post_persists_a_two_int_list_and_advances(client, db):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
    response = client.post(f'/survey/{token}/step/{STEP_NEED_MOST}', data={'need_most': '0,1'})

    assert response.status_code == 302
    assert response.headers['Location'].endswith(f'/survey/{token}/step/{STEP_NEED_MOST + 1}')

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.answers['need_most'] == [0, 1]


@pytest.mark.parametrize(
    'step, field, raw, expected',
    [
        (STEP_HAVE_ENOUGH, 'have_enough', '1,2', [1, 2]),
        (STEP_SUPPORT_TYPE, 'support_type', '0,2', [0, 2]),
    ],
)
def test_triangle_edge_post_persists_on_the_other_two_affected_questions(client, db, step, field, raw, expected):
    """backlog #0010: the coder's own e2e edge-POST test only covered
    `need_most`. `have_enough` and `support_type` are the other 2 of the 3
    affected triangle questions and must round-trip identically."""
    token = _start_new(client)
    _answer_up_to_grid(client, token, INDIVIDUAL)  # gets past need_most/have_enough with corner picks
    client.post(f'/survey/{token}/step/{STEP_PROFILE_GRID}', data={'profile_grid': '1,1'})
    client.post(f'/survey/{token}/step/{STEP_TOPICS}', data={'topics': ['0', '1', '2']})

    response = client.post(f'/survey/{token}/step/{step}', data={field: raw})

    assert response.status_code == 302
    assert response.headers['Location'].endswith(f'/survey/{token}/step/{step + 1}')

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.answers[field] == expected


def test_triangle_edge_pick_rechecks_the_correct_edge_node_on_reget(client):
    """Spec's re-render edge case: after saving an edge pick, GETting the
    step again must re-check that exact edge node — and none of the 3
    corner nodes or the other 2 edge nodes."""
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
    client.post(f'/survey/{token}/step/{STEP_NEED_MOST}', data={'need_most': '1,2'})

    response = client.get(f'/survey/{token}/step/{STEP_NEED_MOST}')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'checked' in _input_tag(body, 'need_most_1_2')
    for other_id in ('need_most_0', 'need_most_1', 'need_most_2', 'need_most_0_1', 'need_most_0_2'):
        assert 'checked' not in _input_tag(body, other_id), f'{other_id} should not be checked'


def test_triangle_corner_pick_does_not_recheck_any_edge_node_on_reget(client):
    """Inverse of the above: a saved corner pick (int) must not accidentally
    satisfy an edge node's `saved_value == [a.index, b.index]` list compare
    (int vs list should never collide)."""
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
    client.post(f'/survey/{token}/step/{STEP_NEED_MOST}', data={'need_most': '2'})

    response = client.get(f'/survey/{token}/step/{STEP_NEED_MOST}')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'checked' in _input_tag(body, 'need_most_2')
    for other_id in ('need_most_0', 'need_most_1', 'need_most_0_1', 'need_most_1_2', 'need_most_0_2'):
        assert 'checked' not in _input_tag(body, other_id), f'{other_id} should not be checked'


def test_survey_completes_when_all_three_triangle_questions_are_skipped(client, db):
    """Spec's untouched-triangle edge case, exercised end-to-end for all 3
    affected questions: skipping every triangle step (no radio posted) must
    still let the submission complete and classify, with `_read_answer`
    returning None for each and the Now/Next narrative simply omitting
    their contribution rather than erroring."""
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
    client.post(f'/survey/{token}/step/{STEP_WHY_REASON}', data={'why_reason': 'Because it matters.'})
    client.post(f'/survey/{token}/step/{STEP_MOTIVATION}', data={'motivation': '0'})
    client.post(f'/survey/{token}/step/{STEP_AMBITION}', data={'ambition': '0'})
    client.post(f'/survey/{token}/step/{STEP_SPACE_TO_PROGRESS}', data={'space_to_progress': '0'})
    client.post(f'/survey/{token}/step/{STEP_NEED_MOST}', data={})
    client.post(f'/survey/{token}/step/{STEP_HAVE_ENOUGH}', data={})
    client.post(f'/survey/{token}/step/{STEP_PROFILE_GRID}', data={'profile_grid': '1,1'})
    client.post(f'/survey/{token}/step/{STEP_TOPICS}', data={'topics': ['0', '1', '2']})
    client.post(f'/survey/{token}/step/{STEP_SUPPORT_TYPE}', data={})
    final = client.post(f'/survey/{token}/step/{STEP_TARGET_GROUPS}', data={'target_groups': '0'})

    assert final.status_code == 302
    assert final.headers['Location'].endswith(f'/survey/{token}/result')

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.persona_id == 'entrepreneur'
    assert submission.answers['need_most'] is None
    assert submission.answers['have_enough'] is None
    assert submission.answers['support_type'] is None

    result = client.get(f'/survey/{token}/result')
    body = result.get_data(as_text=True)
    assert 'Your current sustainability focus' not in body
    assert 'In order to progress your ambitions' not in body


def test_edge_picks_on_all_three_affected_questions_read_correctly_in_result_page_copy(client, db):
    """backlog #0010: an edge pick's joined phrase must read correctly *in
    context* within the full Now/Next sentence on the rendered result page —
    not just as a substring check against the resolver's return value — and
    this must hold for all 3 affected questions, not just `need_most`."""
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
    client.post(f'/survey/{token}/step/{STEP_WHY_REASON}', data={'why_reason': 'Because it matters.'})
    client.post(f'/survey/{token}/step/{STEP_MOTIVATION}', data={'motivation': '0'})
    client.post(f'/survey/{token}/step/{STEP_AMBITION}', data={'ambition': '0'})
    client.post(f'/survey/{token}/step/{STEP_SPACE_TO_PROGRESS}', data={'space_to_progress': '0'})
    client.post(f'/survey/{token}/step/{STEP_NEED_MOST}', data={'need_most': '0,1'})       # edge
    client.post(f'/survey/{token}/step/{STEP_HAVE_ENOUGH}', data={'have_enough': '0,1'})   # edge
    client.post(f'/survey/{token}/step/{STEP_PROFILE_GRID}', data={'profile_grid': '1,1'})
    client.post(f'/survey/{token}/step/{STEP_TOPICS}', data={'topics': ['0', '1', '2']})
    client.post(f'/survey/{token}/step/{STEP_SUPPORT_TYPE}', data={'support_type': '0,1'})  # edge
    final = client.post(f'/survey/{token}/step/{STEP_TARGET_GROUPS}', data={'target_groups': '0'})
    assert final.status_code == 302

    response = client.get(f'/survey/{token}/result')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert (
        'good amount of capacity and knowledge to help achieve your goals'
        in body
    )
    assert 'you are looking for more capacity and knowledge.' in body
    assert (
        'This could be achieved by accessing more information and training '
        'to address this challenge.' in body
    )


# ---------------------------------------------------------------------------
# Result page / radar chart / share / PDF / email — against the new content
# shape (11 real questions, grid-direct one-hot score vector)
# ---------------------------------------------------------------------------

def test_result_page_renders_persona_and_radar_chart(client):
    token, _ = _complete_survey(client)
    response = client.get(f'/survey/{token}/result')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'The Entrepreneur' in body
    assert '<svg' in body
    assert 'Persona fingerprint radar chart' in body


def test_result_page_shows_organisation_wording_persona_description_on_the_org_track(client):
    """backlog #0004: `submission.audience` reaches the web result page's
    persona card, which resolves `description_organisation` once the
    respondent is on the organisation track."""
    token, _ = _complete_survey(client, audience_index=ORGANISATION, grid='1,1')  # -> entrepreneur
    response = client.get(f'/survey/{token}/result')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'Your organisation sees and acts upon the opportunities' in body
    assert 'You see and act upon the opportunities' not in body


def test_result_page_shows_individual_wording_persona_description_on_the_individual_track(client):
    token, _ = _complete_survey(client, audience_index=INDIVIDUAL, grid='1,1')  # -> entrepreneur
    response = client.get(f'/survey/{token}/result')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'You see and act upon the opportunities' in body
    assert 'Your organisation sees and acts upon the opportunities' not in body


def test_result_page_renders_the_labelled_grid_with_the_chosen_persona(client):
    token, _ = _complete_survey(client, grid='2,0')  # -> activist
    response = client.get(f'/survey/{token}/result')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'Your position on the grid' in body
    assert 'The Activist' in body
    assert 'grid-cell--selected' in body


def test_result_page_renders_the_innovation_band_card_after_the_grid(client):
    """backlog #0002: the innovation-curve card sits directly below 'Your
    position on the grid' (and before the share card)."""
    token, _ = _complete_survey(client)  # motivation/ambition/space_to_progress=0, entrepreneur -> Late Majority
    response = client.get(f'/survey/{token}/result')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'Where you sit on the innovation curve' in body
    assert 'Late Majority' in body

    grid_pos = body.index('Your position on the grid')
    innovation_pos = body.index('Where you sit on the innovation curve')
    share_pos = body.index('Share or save your result')
    assert grid_pos < innovation_pos < share_pos


def test_result_page_renders_the_now_next_card_in_the_persona_card(client):
    """backlog #0007 (moved per Tom's follow-up feedback): the Now/Next
    block sits inside the persona card ('Your sustainable who'), directly
    below the persona description and above 'Natural allies' — not as its
    own card after the innovation-curve block."""
    # _complete_survey defaults: topics=[0,1,2] (Water/Food & Drinks/Energy),
    # have_enough=need_most=support_type=target_groups=0.
    token, _ = _complete_survey(client)
    response = client.get(f'/survey/{token}/result')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'Now and next' in body
    # Auto-escaped, not | safe — 'Food & Drinks' must render as '&amp;'.
    assert 'Water, Food &amp; Drinks, and Energy' in body
    assert 'you are looking for more capacity' in body

    description_pos = body.index('Your sustainable who')
    now_next_pos = body.index('Now and next')
    allies_pos = body.index('Natural allies')
    grid_pos = body.index('Your position on the grid')
    assert description_pos < now_next_pos < allies_pos < grid_pos


def test_result_grid_table_structure_is_a_real_3x3_not_a_stacked_column(client):
    """Regression test: `.grid-cell` (display:flex) was once applied directly
    to the result grid's <td>, which overrides the browser's default
    table-cell display and breaks the table out of row/column layout —
    visually all 9 personas stacked into a single column instead of 3x3.
    Guard both ends: the <td> itself must stay a plain, unstyled table cell
    (only `persona-grid-cell-wrap`, which is padding-only in theme.css), and
    the flex-styled `.grid-cell` must live on a nested element instead."""
    token, _ = _complete_survey(client, grid='2,0')  # -> activist
    response = client.get(f'/survey/{token}/result')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '<td class="grid-cell' not in body
    assert body.count('<td class="persona-grid-cell-wrap">') == 9
    assert body.count('class="grid-cell grid-cell--result') == 9
    # 3 data rows (one per y), each headed by its own y-axis row label.
    assert body.count('<th scope="row">') == 3


def test_share_image_returns_png_against_real_content(client):
    token, _ = _complete_survey(client)
    response = client.get(f'/survey/{token}/share.png')
    assert response.status_code == 200
    assert response.mimetype == 'image/png'
    assert response.data.startswith(PNG_MAGIC)


def test_download_pdf_returns_pdf_against_real_content(client):
    token, _ = _complete_survey(client)
    response = client.get(f'/survey/{token}/pdf')
    assert response.status_code == 200
    assert response.mimetype == 'application/pdf'
    assert response.data.startswith(b'%PDF')
    assert 'Entrepreneur' in response.headers['Content-Disposition']


def test_pdf_result_template_renders_the_innovation_band_name(app):
    """generate_result_pdf threads `innovation` into `pdf/result.html` — the
    simplest robust check that the partial is included is rendering the
    template directly with an `innovation` context and asserting the band
    name is present (WeasyPrint's rasterised PDF bytes aren't text-greppable)."""
    from flask import render_template

    persona = {
        'name': 'The Entrepreneur', 'tagline': 't', 'description': 'd',
        'natural_allies': [], 'friends': [], 'necessity': [], 'case_studies': [], 'resources': [],
    }
    innovation = {'band': 'Late Majority', 'score': 5, 'colour': '#e67e22'}

    with app.app_context():
        html = render_template(
            'pdf/result.html', persona=persona, personas={'entrepreneur': persona},
            fingerprint_svg='<svg></svg>', innovation=innovation, audience=None,
        )
    assert 'Where you sit on the innovation curve' in html
    assert 'Late Majority' in html


def test_pdf_result_template_renders_the_now_next_statements(app):
    """generate_result_pdf threads `now_next` into `pdf/result.html` — the
    simplest robust check that the partial is included is rendering the
    template directly with a `now_next` context and asserting the statement
    text is present (WeasyPrint's rasterised PDF bytes aren't
    text-greppable)."""
    from flask import render_template

    persona = {
        'name': 'The Entrepreneur', 'tagline': 't', 'description': 'd',
        'natural_allies': [], 'friends': [], 'necessity': [], 'case_studies': [], 'resources': [],
    }
    now_next = {'now': 'Now sentence.', 'next': 'Next sentence.'}

    with app.app_context():
        html = render_template(
            'pdf/result.html', persona=persona, personas={'entrepreneur': persona},
            fingerprint_svg='<svg></svg>', now_next=now_next, audience=None,
        )
    assert 'Now and next' in html
    assert 'Now sentence.' in html
    assert 'Next sentence.' in html


def test_pdf_result_template_autoescapes_ampersand_in_now_next_statement(app):
    """The now_next partial has no `| safe` — a statement text containing a
    raw '&' (e.g. from a 'Food & Drinks' topic label baked into the resolved
    sentence) must render as '&amp;' in the PDF's source HTML, not leak
    unescaped markup."""
    from flask import render_template

    persona = {
        'name': 'The Entrepreneur', 'tagline': 't', 'description': 'd',
        'natural_allies': [], 'friends': [], 'necessity': [], 'case_studies': [], 'resources': [],
    }
    now_next = {'now': 'Your focus is Water, Food & Drinks, and Energy.', 'next': None}

    with app.app_context():
        html = render_template(
            'pdf/result.html', persona=persona, personas={'entrepreneur': persona},
            fingerprint_svg='<svg></svg>', now_next=now_next, audience=None,
        )
    assert 'Water, Food &amp; Drinks, and Energy' in html
    assert 'Food & Drinks' not in html


def test_email_templates_render_the_innovation_band_name(app):
    """Unit-level check (mirroring how test_sharing.py exercises email
    bodies) that both email/result.txt and email/result.html render the
    band name when given an `innovation` context."""
    from flask import render_template

    persona = {'name': 'The Entrepreneur', 'tagline': 't', 'description': 'd'}
    innovation = {'band': 'Late Majority', 'score': 5, 'colour': '#e67e22'}

    with app.app_context():
        text_body = render_template(
            'email/result.txt', persona=persona, result_url='https://example.com/r',
            innovation=innovation, audience=None,
        )
        html_body = render_template(
            'email/result.html', persona=persona, result_url='https://example.com/r',
            innovation=innovation, audience=None,
        )

    assert 'Late Majority' in text_body
    assert 'Late Majority' in html_body


def test_email_templates_render_the_now_next_statements(app):
    """Unit-level check (mirroring how the innovation-curve email test
    works) that both email/result.txt and email/result.html render the
    Now/Next statements when given a `now_next` context."""
    from flask import render_template

    persona = {'name': 'The Entrepreneur', 'tagline': 't', 'description': 'd'}
    now_next = {'now': 'Now sentence.', 'next': 'Next sentence.'}

    with app.app_context():
        text_body = render_template(
            'email/result.txt', persona=persona, result_url='https://example.com/r',
            now_next=now_next, audience=None,
        )
        html_body = render_template(
            'email/result.html', persona=persona, result_url='https://example.com/r',
            now_next=now_next, audience=None,
        )

    assert 'Now sentence.' in text_body
    assert 'Next sentence.' in text_body
    assert 'Now sentence.' in html_body
    assert 'Next sentence.' in html_body


def test_email_html_template_autoescapes_ampersand_in_now_next_statement(app):
    """email/result.html has no `| safe` on now_next.now/next either — a
    statement containing a raw '&' must escape to '&amp;' there too, not
    just on the web result page. The plain-text sibling (result.txt) is not
    HTML and must NOT escape it."""
    from flask import render_template

    persona = {'name': 'The Entrepreneur', 'tagline': 't', 'description': 'd'}
    now_next = {'now': 'Your focus is Water, Food & Drinks, and Energy.', 'next': None}

    with app.app_context():
        html_body = render_template(
            'email/result.html', persona=persona, result_url='https://example.com/r',
            now_next=now_next, audience=None,
        )
        text_body = render_template(
            'email/result.txt', persona=persona, result_url='https://example.com/r',
            now_next=now_next, audience=None,
        )

    assert 'Water, Food &amp; Drinks, and Energy' in html_body
    assert 'Food & Drinks' not in html_body
    # Plain text: no HTML entity encoding expected.
    assert 'Water, Food & Drinks, and Energy' in text_body


def test_email_result_route_reachable_against_real_content(client, app):
    """No MAIL_SERVER configured in tests — confirms the route still runs
    the full generate-context pipeline (fingerprint SVG, persona lookup)
    against the new content shape without erroring before hitting the
    not-configured guard."""
    assert app.config.get('MAIL_SERVER') is None
    token, _ = _complete_survey(client)
    response = client.post(
        f'/survey/{token}/email', data={'email': 'someone@example.com'}, follow_redirects=True,
    )
    assert response.status_code == 200
    assert "isn&#39;t configured" in response.get_data(as_text=True) \
        or "isn't configured" in response.get_data(as_text=True)


# ---------------------------------------------------------------------------
# Failure case — malformed grid value never reaches the classifier as a hit
# ---------------------------------------------------------------------------

def test_grid_step_with_malformed_value_is_treated_as_no_selection(client, db):
    """A garbage (non 'x,y') value for the grid radio group must be rejected
    by the same mandatory guard as no selection at all — not silently
    accepted or crash the route."""
    token = _start_new(client)
    _answer_up_to_grid(client, token, INDIVIDUAL)

    response = client.post(f'/survey/{token}/step/{STEP_PROFILE_GRID}', data={'profile_grid': 'garbage'})

    assert response.status_code == 200
    assert b'Please select a position on the grid to continue.' in response.data
    submission = db.session.query(Submission).filter_by(token=token).one()
    assert 'profile_grid' not in submission.answers
