"""backlog #0017 Part A: the `explanation` help-text field, exercised through
the real HTTP layer against the real `content/survey.yaml` (not the small
loader-level checks in test_loader.py). Confirms it renders where the
content declares it, stays absent where it doesn't (no empty artifact),
survives multi-line content as visible line breaks rather than raw HTML,
and never leaks onto a result surface (step-page-only per spec).

Step numbers mirror the real-survey layout documented in
test_real_survey_e2e.py (order: router, motivation, ambition,
space_to_progress, need_most, have_enough, profile (combined), topics,
support_type, target_groups, why_reason — backlog #0017 Part B replaced the
old single `profile_grid` step with the profile_approach/profile_scope pair,
briefly as two separate steps before a same-branch follow-up tweak merged
them back onto one combined step).
"""
import os

import pytest

from app.survey.loader import clear_survey_cache

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_SURVEY_PATH = os.path.join(REPO_ROOT, 'content', 'survey.yaml')

INDIVIDUAL = 0

STEP_RESPONDENT_TYPE = 1
STEP_MOTIVATION = 2
STEP_AMBITION = 3
STEP_SPACE_TO_PROGRESS = 4
STEP_NEED_MOST = 5
STEP_HAVE_ENOUGH = 6
STEP_PROFILE = 7
STEP_TOPICS = 8
STEP_SUPPORT_TYPE = 9
STEP_TARGET_GROUPS = 10
STEP_WHY_REASON = 11


@pytest.fixture(autouse=True)
def _use_real_survey(app):
    app.config['SURVEY_PATH'] = REAL_SURVEY_PATH
    clear_survey_cache()
    yield
    clear_survey_cache()


def _start_new(client):
    response = client.get('/survey/start')
    assert response.status_code == 302
    return response.headers['Location'].split('/survey/')[1].split('/step/')[0]


def _answer_up_to_grid(client, token, audience_index):
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(audience_index)})
    client.post(f'/survey/{token}/step/{STEP_MOTIVATION}', data={'motivation': '0'})
    client.post(f'/survey/{token}/step/{STEP_AMBITION}', data={'ambition': '0'})
    client.post(f'/survey/{token}/step/{STEP_SPACE_TO_PROGRESS}', data={'space_to_progress': '0'})
    client.post(f'/survey/{token}/step/{STEP_NEED_MOST}', data={'need_most': '0'})
    client.post(f'/survey/{token}/step/{STEP_HAVE_ENOUGH}', data={'have_enough': '0'})


def _complete_survey(client, audience_index=INDIVIDUAL, approach='1', scope='1', why_reason='Because it matters.'):
    token = _start_new(client)
    _answer_up_to_grid(client, token, audience_index)
    client.post(f'/survey/{token}/step/{STEP_PROFILE}', data={'profile_approach': approach, 'profile_scope': scope})
    client.post(f'/survey/{token}/step/{STEP_TOPICS}', data={'topics': ['0', '1', '2']})
    client.post(f'/survey/{token}/step/{STEP_SUPPORT_TYPE}', data={'support_type': '0'})
    client.post(f'/survey/{token}/step/{STEP_TARGET_GROUPS}', data={'target_groups': '0'})
    why_data = {} if why_reason is None else {'why_reason': why_reason}
    final = client.post(f'/survey/{token}/step/{STEP_WHY_REASON}', data=why_data)
    return token, final


# ---------------------------------------------------------------------------
# Happy path — explanation renders where the content declares it
# ---------------------------------------------------------------------------

def test_space_to_progress_step_renders_its_explanation(client):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
    client.post(f'/survey/{token}/step/{STEP_MOTIVATION}', data={'motivation': '0'})
    client.post(f'/survey/{token}/step/{STEP_AMBITION}', data={'ambition': '0'})

    response = client.get(f'/survey/{token}/step/{STEP_SPACE_TO_PROGRESS}')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'class="question-explanation' in body
    assert (
        'This question is asking you to consider how much you are currently '
        'committed' in body
    )
    # Reworded prompt is present too.
    assert 'What is the current balance between your commitments and capacity?' in body


def test_need_most_and_have_enough_and_support_type_steps_render_their_explanations(client):
    token = _start_new(client)
    _answer_up_to_grid(client, token, INDIVIDUAL)

    need_most_body = client.get(f'/survey/{token}/step/{STEP_NEED_MOST}').get_data(as_text=True)
    assert 'class="question-explanation' in need_most_body
    assert 'consider your additional requirements or needs' in need_most_body

    have_enough_body = client.get(f'/survey/{token}/step/{STEP_HAVE_ENOUGH}').get_data(as_text=True)
    assert 'class="question-explanation' in have_enough_body
    assert 'requirements or needs you may have that are already being met' in have_enough_body

    client.post(f'/survey/{token}/step/{STEP_PROFILE}', data={'profile_approach': '1', 'profile_scope': '1'})
    client.post(f'/survey/{token}/step/{STEP_TOPICS}', data={'topics': ['0', '1', '2']})
    support_type_body = client.get(f'/survey/{token}/step/{STEP_SUPPORT_TYPE}').get_data(as_text=True)
    assert 'class="question-explanation' in support_type_body
    assert 'consider what kind of assistance would help you achieve your goals' in support_type_body
    # Reworded prompt for this question too.
    assert 'What type of assistance do you desire?' in support_type_body
    assert 'What type of support do you desire?' not in support_type_body


# ---------------------------------------------------------------------------
# Edge case — no `.question-explanation` artifact when the question has none
# ---------------------------------------------------------------------------

def test_target_groups_step_renders_no_explanation_element_at_all(client):
    """`target_groups` has no `explanation` key in survey.yaml — the
    template's `{% if question.explanation %}` guard must render nothing,
    not an empty `<p class="question-explanation">`."""
    token = _start_new(client)
    _answer_up_to_grid(client, token, INDIVIDUAL)
    client.post(f'/survey/{token}/step/{STEP_PROFILE}', data={'profile_approach': '1', 'profile_scope': '1'})
    client.post(f'/survey/{token}/step/{STEP_TOPICS}', data={'topics': ['0', '1', '2']})
    client.post(f'/survey/{token}/step/{STEP_SUPPORT_TYPE}', data={'support_type': '0'})

    response = client.get(f'/survey/{token}/step/{STEP_TARGET_GROUPS}')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'question-explanation' not in body
    # Reworded prompt present, old prompt gone.
    assert 'Who are you trying to work with?' in body
    assert 'What target groups would you like to collaborate with the most?' not in body


def test_respondent_type_router_step_renders_no_explanation_element(client):
    """The router question (step 1) also has no `explanation` — a second,
    unrelated question type confirming the guard isn't accidentally
    type-gated to only 'hide' correctly on `single`/triangle types."""
    token = _start_new(client)
    response = client.get(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'question-explanation' not in body


# ---------------------------------------------------------------------------
# Multi-line content — real newlines + CSS pre-line, never raw HTML
# ---------------------------------------------------------------------------

def test_multiline_explanation_renders_as_escaped_text_with_newlines_not_br_tags(client):
    token = _start_new(client)
    _answer_up_to_grid(client, token, INDIVIDUAL)

    body = client.get(f'/survey/{token}/step/{STEP_NEED_MOST}').get_data(as_text=True)

    assert 'Capacity refers to skills, time and/or resources.' in body
    assert 'Knowledge refers to information, training and/or applied practice' in body
    assert '<br>' not in body
    assert '<br/>' not in body
    assert '<br />' not in body
    # The bullet lines are joined by a real newline in the source HTML (the
    # CSS `white-space: pre-line` rule is what turns this into a visible
    # line break in the browser, not markup).
    explanation_element = body.split('question-explanation')[1].split('</p>')[0]
    assert '\n' in explanation_element


# ---------------------------------------------------------------------------
# Confirmations from the spec's "Not touched" section — step-page-only
# ---------------------------------------------------------------------------

def test_explanation_text_does_not_appear_on_the_result_page(client):
    token, _ = _complete_survey(client)
    response = client.get(f'/survey/{token}/result')
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'question-explanation' not in body
    assert 'consider how much you are currently committed' not in body
    assert 'consider what kind of assistance would help you achieve your goals' not in body


def test_explanation_text_does_not_appear_in_the_pdf_result_template(app):
    """generate_result_pdf's `pdf/result.html` never receives a `question`
    context at all — rendering it directly (as the other PDF checks in this
    suite do) confirms no stray explanation text leaks in."""
    from flask import render_template

    persona = {
        'name': 'The Entrepreneur', 'tagline': 't', 'description': 'd',
        'natural_allies': [], 'friends': [], 'necessity': [], 'case_studies': [], 'resources': [],
    }

    with app.app_context():
        html = render_template(
            'pdf/result.html', persona=persona, personas={'entrepreneur': persona},
            fingerprint_svg='<svg></svg>', audience=None,
        )
    assert 'question-explanation' not in html


# ---------------------------------------------------------------------------
# Verbatim quirks preserved from the source template (spec's OPEN QUESTIONS)
# ---------------------------------------------------------------------------

def test_space_to_progress_verbatim_quirks_are_not_autocorrected(client):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
    client.post(f'/survey/{token}/step/{STEP_MOTIVATION}', data={'motivation': '0'})
    client.post(f'/survey/{token}/step/{STEP_AMBITION}', data={'ambition': '0'})

    body = client.get(f'/survey/{token}/step/{STEP_SPACE_TO_PROGRESS}').get_data(as_text=True)

    # "commited" (one t) — must not have been silently corrected to "committed".
    assert 'No capacity, fully commited' in body
    assert 'No capacity, fully committed' not in body
    # "our" retained even though the rest of the question is audience-neutral.
    assert 'Balanced between our commitments and capacity' in body


# ---------------------------------------------------------------------------
# Failure case — malformed explanation content is rejected at load time,
# never reaches the template layer (loader.py enforces this before the app
# boots; exercised end-to-end via a broken SURVEY_PATH here rather than
# repeating the unit-level checks already in test_loader.py).
# ---------------------------------------------------------------------------

def test_app_start_fails_fast_when_survey_yaml_has_an_empty_explanation(app, tmp_path):
    import yaml

    from app.survey.loader import SurveyConfigError, load_survey

    with open(REAL_SURVEY_PATH, encoding='utf-8') as f:
        raw = yaml.safe_load(f)

    for question in raw['questions']:
        if question['id'] == 'target_groups':
            question['explanation'] = ''  # invalid: present but empty
            break
    else:
        pytest.fail('target_groups not found in content/survey.yaml')

    broken_path = tmp_path / 'broken_survey.yaml'
    broken_path.write_text(yaml.safe_dump(raw), encoding='utf-8')

    with pytest.raises(SurveyConfigError):
        load_survey(str(broken_path))
