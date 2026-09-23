"""Tester verification for backlog #0042 (carry persona visual identity into
the survey flow). Covers spec.md's Tests list:

  1. Home page renders all 9 persona names + inline icons + the "One of
     these is you" label.
  2. Home page still 200s with no persona-preview-grid when survey.yaml is
     missing.
  3. Steps 1-7 (real survey) never show the badge -- including the profile
     step itself, even once it has been answered (the `step <= profile_step`
     boundary).
  4. Step 8 (GET, right after posting step 7): badge, persona name, an
     inline icon, "Your sustainable who", and the one-off reveal class.
  5. Steps 9-11: badge present, reveal class gone.
  6. Back-navigation to step 5 after the profile step was answered: no
     badge.
  7. A fixture survey with no `profile_matrix` never shows a badge, on any
     step.
  8. theme.css degrades the reveal to `animation: none` under
     prefers-reduced-motion, and the mobile breakpoint is still the file's
     last block.
  9. "Question 11 of 11" still renders on the final step (progress-copy
     regression guard).

Plus one extra case closing the coder's flagged gap: the reveal-once
`profile_step` arithmetic, spot-checked only against the real 11-step survey,
against tests/fixtures/survey_grid.yaml (its own profile_matrix, a different
combined-step position (5, not 7) and total (6, not 11)).

Reuses the real-survey fixture pattern and step constants from
test_real_survey_e2e.py (approach='1', scope='1' -> The Entrepreneur).
"""
import os
import re

import pytest

from app.survey.loader import clear_survey_cache

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_SURVEY_PATH = os.path.join(REPO_ROOT, 'content', 'survey.yaml')
MISSING_SURVEY_PATH = os.path.join(REPO_ROOT, 'content', 'does-not-exist.yaml')
SURVEY_MIN_PATH = os.path.join(REPO_ROOT, 'tests', 'fixtures', 'survey_min.yaml')
SURVEY_GRID_PATH = os.path.join(REPO_ROOT, 'tests', 'fixtures', 'survey_grid.yaml')
THEME_CSS_PATH = os.path.join(REPO_ROOT, 'app', 'static', 'css', 'theme.css')

INDIVIDUAL = 0
ORGANISATION = 1

# Step numbers for the real 11-step survey -- see test_real_survey_e2e.py
# for the full backlog history behind this numbering.
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
TOTAL_STEPS = 11

ALL_PERSONA_NAMES = [
    'The Accountant', 'The Implementer', 'The Inventor', 'The Architect',
    'The Communicator', 'The Advocate', 'The Connector', 'The Cooperator',
    'The Entrepreneur',
]


@pytest.fixture(autouse=True)
def _use_real_survey(app):
    # Config's default already, but set + clear explicitly so this module is
    # correct regardless of what ran before it (matches
    # test_real_survey_e2e.py's own fixture).
    app.config['SURVEY_PATH'] = REAL_SURVEY_PATH
    clear_survey_cache()
    yield
    clear_survey_cache()


def _start_new(client):
    response = client.get('/survey/start')
    assert response.status_code == 302
    return response.headers['Location'].split('/survey/')[1].split('/step/')[0]


def _answer_up_to_grid(client, token, audience_index=INDIVIDUAL):
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(audience_index)})
    client.post(f'/survey/{token}/step/{STEP_MOTIVATION}', data={'motivation': '4'})
    client.post(f'/survey/{token}/step/{STEP_AMBITION}', data={'ambition': '4'})
    client.post(f'/survey/{token}/step/{STEP_SPACE_TO_PROGRESS}', data={'space_to_progress': '4'})
    client.post(f'/survey/{token}/step/{STEP_NEED_MOST}', data={'need_most': '0'})
    client.post(f'/survey/{token}/step/{STEP_HAVE_ENOUGH}', data={'have_enough': '0'})


def _answer_profile(client, token, approach='1', scope='1'):
    """approach='1', scope='1' -> The Entrepreneur (per profile_matrix)."""
    return client.post(
        f'/survey/{token}/step/{STEP_PROFILE}',
        data={'profile_approach': approach, 'profile_scope': scope},
    )


def _advance_to(client, token, target_step):
    """POST steps 8..target_step-1 with valid answers. Assumes steps 1-7
    (up to and including the profile pair) are already answered; leaves
    `target_step` itself unanswered so it can be GET-inspected."""
    if target_step > STEP_TOPICS:
        client.post(f'/survey/{token}/step/{STEP_TOPICS}', data={'topics': ['0', '1', '2']})
    if target_step > STEP_SUPPORT_TYPE:
        client.post(f'/survey/{token}/step/{STEP_SUPPORT_TYPE}', data={'support_type': '0'})
    if target_step > STEP_TARGET_GROUPS:
        client.post(f'/survey/{token}/step/{STEP_TARGET_GROUPS}', data={'target_groups': '0'})


def _normalised_css():
    with open(THEME_CSS_PATH, encoding='utf-8') as f:
        raw = f.read()
    return re.sub(r'\s+', ' ', raw)


# ---------------------------------------------------------------------------
# 1. Home page -- static, undifferentiated persona preview grid
# ---------------------------------------------------------------------------

def test_home_page_renders_all_nine_persona_names_and_inline_icons(client):
    body = client.get('/').get_data(as_text=True)

    assert 'One of these is you' in body
    for name in ALL_PERSONA_NAMES:
        assert name in body, f'{name} missing from the home page'
    assert body.count('<svg') == 9


# ---------------------------------------------------------------------------
# 2. Broken/missing survey.yaml -- home page still 200s, no persona grid
# ---------------------------------------------------------------------------

def test_home_page_200s_with_no_persona_grid_when_survey_yaml_is_missing(client):
    client.application.config['SURVEY_PATH'] = MISSING_SURVEY_PATH
    clear_survey_cache()
    try:
        response = client.get('/')
        body = response.get_data(as_text=True)

        assert response.status_code == 200
        assert 'persona-preview-grid' not in body
    finally:
        client.application.config['SURVEY_PATH'] = REAL_SURVEY_PATH
        clear_survey_cache()


# ---------------------------------------------------------------------------
# 3. Steps 1-7 -- no badge, no persona-name leak, before/at the profile step
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('step', [
    STEP_RESPONDENT_TYPE, STEP_MOTIVATION, STEP_AMBITION, STEP_SPACE_TO_PROGRESS,
    STEP_NEED_MOST, STEP_HAVE_ENOUGH,
])
def test_no_badge_before_the_profile_step_is_answered(client, step):
    token = _start_new(client)
    _answer_up_to_grid(client, token, INDIVIDUAL)

    body = client.get(f'/survey/{token}/step/{step}').get_data(as_text=True)

    assert 'persona-badge' not in body
    assert 'The Entrepreneur' not in body


def test_no_badge_on_the_profile_step_itself_even_once_it_is_answered(client):
    """`step <= profile_step` covers the profile step's own GET too --
    resolve_profile_persona already resolves 'entrepreneur' by this point,
    but the badge must not appear until the step after (spec: "A GET of
    step 7 itself must show no badge")."""
    token = _start_new(client)
    _answer_up_to_grid(client, token, INDIVIDUAL)
    _answer_profile(client, token)  # -> entrepreneur, resolvable from here on

    body = client.get(f'/survey/{token}/step/{STEP_PROFILE}').get_data(as_text=True)

    assert 'persona-badge' not in body
    assert 'The Entrepreneur' not in body


# ---------------------------------------------------------------------------
# 4. Step 8 -- badge appears, with the one-off reveal
# ---------------------------------------------------------------------------

def test_step_eight_shows_the_badge_with_the_reveal_class(client):
    token = _start_new(client)
    _answer_up_to_grid(client, token, INDIVIDUAL)
    _answer_profile(client, token)  # -> entrepreneur

    body = client.get(f'/survey/{token}/step/{STEP_TOPICS}').get_data(as_text=True)

    assert 'persona-badge' in body
    assert 'The Entrepreneur' in body
    assert '<svg' in body
    assert 'Your sustainable who' in body
    assert 'persona-badge--reveal' in body


# ---------------------------------------------------------------------------
# 5. Steps 9-11 -- badge persists, reveal class does not
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('step', [STEP_SUPPORT_TYPE, STEP_TARGET_GROUPS, STEP_WHY_REASON])
def test_badge_persists_without_the_reveal_class_on_later_steps(client, step):
    token = _start_new(client)
    _answer_up_to_grid(client, token, INDIVIDUAL)
    _answer_profile(client, token)  # -> entrepreneur
    _advance_to(client, token, step)

    body = client.get(f'/survey/{token}/step/{step}').get_data(as_text=True)

    assert 'persona-badge' in body
    assert 'The Entrepreneur' in body
    assert 'persona-badge--reveal' not in body


# ---------------------------------------------------------------------------
# 6. Back-navigation
# ---------------------------------------------------------------------------

def test_back_navigation_to_step_five_after_the_profile_step_shows_no_badge(client):
    token = _start_new(client)
    _answer_up_to_grid(client, token, INDIVIDUAL)
    _answer_profile(client, token)  # -> entrepreneur

    body = client.get(f'/survey/{token}/step/{STEP_NEED_MOST}').get_data(as_text=True)

    assert 'persona-badge' not in body
    assert 'The Entrepreneur' not in body


# ---------------------------------------------------------------------------
# 7. A survey with no profile_matrix never shows a badge
# ---------------------------------------------------------------------------

def test_fixture_survey_without_profile_matrix_never_shows_a_badge(client):
    client.application.config['SURVEY_PATH'] = SURVEY_MIN_PATH
    clear_survey_cache()
    try:
        token = _start_new(client)
        client.post(f'/survey/{token}/step/1', data={'q_single': '0'})
        client.post(f'/survey/{token}/step/2', data={'q_multi': []})
        client.post(f'/survey/{token}/step/3', data={'q_spectrum': '0'})

        for step in (1, 2, 3, 4):
            body = client.get(f'/survey/{token}/step/{step}').get_data(as_text=True)
            assert 'persona-badge' not in body
    finally:
        client.application.config['SURVEY_PATH'] = REAL_SURVEY_PATH
        clear_survey_cache()


# ---------------------------------------------------------------------------
# 8. theme.css -- reduced-motion degradation + mobile breakpoint still last
# ---------------------------------------------------------------------------

def test_theme_css_disables_the_persona_badge_reveal_under_reduced_motion():
    css = _normalised_css()

    match = re.search(r'@media \(prefers-reduced-motion: reduce\) \{(.*?)\} \}', css)
    assert match, 'no @media (prefers-reduced-motion: reduce) block found in theme.css'
    reduced_motion_block = match.group(1)
    assert re.search(r'\.persona-badge--reveal\s*\{[^}]*animation:\s*none', reduced_motion_block)


def test_theme_css_mobile_breakpoint_is_still_the_last_block():
    """Mirrors test_mobile_responsive_layout.py's own
    test_theme_css_has_exactly_one_mobile_breakpoint_stacking_the_spectrum_widget
    -- confirm the new persona CSS didn't displace the mobile breakpoint
    from being the file's last block."""
    css = _normalised_css()

    assert css.count('@media (max-width: 767.98px)') == 1
    match = re.search(r'@media \(max-width: 767\.98px\) \{(.*)\} \}\s*$', css, re.DOTALL)
    assert match, 'mobile breakpoint is no longer the last block in theme.css'


# ---------------------------------------------------------------------------
# 9. Progress copy regression guard
# ---------------------------------------------------------------------------

def test_question_x_of_y_progress_copy_still_renders_on_the_final_step(client):
    token = _start_new(client)
    _answer_up_to_grid(client, token, INDIVIDUAL)
    _answer_profile(client, token)
    _advance_to(client, token, STEP_WHY_REASON)

    body = client.get(f'/survey/{token}/step/{STEP_WHY_REASON}').get_data(as_text=True)

    assert f'Question {STEP_WHY_REASON} of {TOTAL_STEPS}' in body


# ---------------------------------------------------------------------------
# Gap check (coder's report): reveal-once step arithmetic on an audience
# track with a different step count than the real survey's 11.
# survey_grid.yaml has its own profile_matrix, but the combined profile step
# sits at step 5 (not 7) of a 6-step total (not 11) -- confirms
# _persona_badge_context derives profile_step from survey_steps() fresh
# rather than relying on the real survey's numbers.
# ---------------------------------------------------------------------------

def test_badge_reveal_arithmetic_holds_on_a_fixture_with_a_different_step_count(client):
    client.application.config['SURVEY_PATH'] = SURVEY_GRID_PATH
    clear_survey_cache()
    try:
        token = _start_new(client)
        client.post(f'/survey/{token}/step/1', data={'respondent_type': str(INDIVIDUAL)})
        client.post(f'/survey/{token}/step/2', data={'q_worded': '0'})
        client.post(f'/survey/{token}/step/3', data={'q_triangle': '0'})
        client.post(f'/survey/{token}/step/4', data={'q_multi_exact': ['0', '1']})

        # Steps 1-4: profile not yet answered -- no badge.
        for step in (1, 2, 3, 4):
            body = client.get(f'/survey/{token}/step/{step}').get_data(as_text=True)
            assert 'persona-badge' not in body

        client.post(
            f'/survey/{token}/step/5',
            data={'profile_approach': '1', 'profile_scope': '1'},
        )  # -> entrepreneur, per survey_grid.yaml's profile_matrix

        # Step 5 (the combined profile step here, not 7): still no badge.
        body_step5 = client.get(f'/survey/{token}/step/5').get_data(as_text=True)
        assert 'persona-badge' not in body_step5

        # Step 6 -- the step immediately after the combined profile step on
        # THIS fixture (not 8, as on the real survey): badge, with reveal.
        body_step6 = client.get(f'/survey/{token}/step/6').get_data(as_text=True)
        assert 'persona-badge' in body_step6
        assert 'The Entrepreneur' in body_step6
        assert 'persona-badge--reveal' in body_step6
    finally:
        client.application.config['SURVEY_PATH'] = REAL_SURVEY_PATH
        clear_survey_cache()
