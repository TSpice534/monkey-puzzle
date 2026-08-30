"""Independent tester verification for backlog #0032 (hover/tap persona
summary popup on the result-page grid).

Covers, per spec.md:
  1. All 9 cells get the popover on the real survey (individual track).
  2. The selected cell is included (decision 3 — every cell behaves
     identically, no dead cell for the user to discover).
  3. The popover title is the persona name, the body carries the tagline and
     description separated by the `&#10;&#10;` plain-text separator (decision
     2 — no `html: true`).
  4. The body is audience-aware, resolved via the same `persona_description()`
     macro `_persona_card.html` already uses.
  5. The body is escaped like any other auto-escaped Jinja attribute.
  6. A persona with no tagline/description gets no popover attributes at all
     (edge case 1 in spec.md) — an empty popover and a focusable dead stop
     are both worse than nothing.
  7. The init script itself — trigger/placement/container/customClass, and
     that no `html: true`/`sanitize: false` ever appears.
  8. No init script (and no popover attributes) when the survey has no grid.
  9. The three new theme.css rules exist, and the mobile breakpoint is still
     the last block in the file (mirrors
     `test_theme_css_mobile_breakpoint_still_last_block_with_grid_legend_rules`
     in test_grid_relationship_colouring.py).
"""
import os
import re

import pytest
from flask import render_template

from app.models import Submission
from app.survey.loader import clear_survey_cache

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_SURVEY_PATH = os.path.join(REPO_ROOT, 'content', 'survey.yaml')
SURVEY_MIN_PATH = os.path.join(REPO_ROOT, 'tests', 'fixtures', 'survey_min.yaml')
THEME_CSS_PATH = os.path.join(REPO_ROOT, 'app', 'static', 'css', 'theme.css')

INDIVIDUAL = 0
ORGANISATION = 1

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


# ---------------------------------------------------------------------------
# Template-level synthetic grid — full control over persona shape
# ---------------------------------------------------------------------------

def _grid_question():
    return {
        'x_axis': {'label': 'Scope', 'options': ['Scope 0', 'Scope 1', 'Scope 2']},
        'y_axis': {'label': 'Approach', 'options': ['Approach 0', 'Approach 1', 'Approach 2']},
        'cells': [
            {'x': x, 'y': y, 'persona': f'p{x}{y}'}
            for y in [0, 1, 2] for x in [0, 1, 2]
        ],
    }


def _synthetic_personas():
    """3x3 layout (x, y). Hand-built persona dicts carry only `id`/`name` —
    same shape as test_grid_relationship_colouring.py's fixture — so
    `has_popover` must be false for every cell here."""
    ids = [f'p{x}{y}' for y in [0, 1, 2] for x in [0, 1, 2]]
    return {pid: {'id': pid, 'name': f'Persona {pid}'} for pid in ids}


def _render_grid(app, persona_id='p11', grid_selected=(1, 1), personas=None, persona=None, audience=None):
    personas = personas if personas is not None else _synthetic_personas()
    persona = persona if persona is not None else personas[persona_id]
    with app.app_context():
        return render_template(
            'survey/_result_grid.html',
            grid_question=_grid_question(),
            grid_selected=list(grid_selected) if grid_selected is not None else None,
            personas=personas,
            persona=persona,
            audience=audience,
        )


CELL_RE = re.compile(r'<div class="(grid-cell grid-cell--result[^"]*)"[^>]*>(.*?)</div>', re.DOTALL)
CELL_OPEN_TAG_RE = re.compile(r'<div class="grid-cell grid-cell--result[^"]*"[^>]*>')


def _cells(html):
    return CELL_RE.findall(html)


def _open_tags(html):
    """Every cell's full opening `<div ...>` tag, attributes and all — unlike
    `_cells`, which (by design, mirroring test_grid_relationship_colouring.py)
    only captures the class attribute."""
    return CELL_OPEN_TAG_RE.findall(html)


# ---------------------------------------------------------------------------
# Real-survey helpers — same shape as test_grid_relationship_colouring.py
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_cache_around_each_test():
    clear_survey_cache()
    yield
    clear_survey_cache()


def _start_new(client):
    response = client.get('/survey/start')
    assert response.status_code == 302
    return response.headers['Location'].split('/survey/')[1].split('/step/')[0]


def _complete_survey_real(client, approach, scope, audience_index=INDIVIDUAL):
    client.application.config['SURVEY_PATH'] = REAL_SURVEY_PATH
    clear_survey_cache()
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(audience_index)})
    client.post(f'/survey/{token}/step/{STEP_MOTIVATION}', data={'motivation': '0'})
    client.post(f'/survey/{token}/step/{STEP_AMBITION}', data={'ambition': '0'})
    client.post(f'/survey/{token}/step/{STEP_SPACE_TO_PROGRESS}', data={'space_to_progress': '0'})
    client.post(f'/survey/{token}/step/{STEP_NEED_MOST}', data={'need_most': '0'})
    client.post(f'/survey/{token}/step/{STEP_HAVE_ENOUGH}', data={'have_enough': '0'})
    client.post(f'/survey/{token}/step/{STEP_PROFILE}', data={'profile_approach': approach, 'profile_scope': scope})
    client.post(f'/survey/{token}/step/{STEP_TOPICS}', data={'topics': ['0', '1', '2']})
    client.post(f'/survey/{token}/step/{STEP_SUPPORT_TYPE}', data={'support_type': '0'})
    client.post(f'/survey/{token}/step/{STEP_TARGET_GROUPS}', data={'target_groups': '0'})
    client.post(f'/survey/{token}/step/{STEP_WHY_REASON}', data={'why_reason': 'Because it matters.'})
    return token


def _cell_content_attr(open_tag, attr):
    match = re.search(attr + r'="([^"]*)"', open_tag)
    assert match, f'{attr} not found in {open_tag!r}'
    return match.group(1)


# ---------------------------------------------------------------------------
# 1. All 9 cells get the popover — real survey, individual track
# ---------------------------------------------------------------------------

def test_all_nine_cells_get_the_popover_real_survey_individual(client, db):
    token = _complete_survey_real(client, approach='1', scope='1')  # -> entrepreneur
    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.persona_id == 'entrepreneur'

    body = client.get(f'/survey/{token}/result').get_data(as_text=True)
    open_tags = _open_tags(body)
    assert len(open_tags) == 9
    # `body.count(...)` would also match the init script's own CSS selector
    # (`document.querySelectorAll('.grid-cell--result[data-bs-toggle="popover"]')`),
    # so count occurrences within the cells' own opening tags instead.
    assert sum(tag.count('data-bs-toggle="popover"') for tag in open_tags) == 9
    assert sum(tag.count('tabindex="0"') for tag in open_tags) == 9


# ---------------------------------------------------------------------------
# 2. The selected cell is included (decision 3)
# ---------------------------------------------------------------------------

def test_selected_cell_also_carries_the_popover(client, db):
    token = _complete_survey_real(client, approach='1', scope='1')  # -> entrepreneur
    body = client.get(f'/survey/{token}/result').get_data(as_text=True)

    selected_tag = next(
        tag for tag in _open_tags(body) if 'grid-cell--selected' in tag
    )
    assert 'data-bs-toggle="popover"' in selected_tag
    assert 'tabindex="0"' in selected_tag


# ---------------------------------------------------------------------------
# 3. Title is the persona name, body carries tagline + description
# ---------------------------------------------------------------------------

def test_popover_title_is_persona_name_and_body_carries_tagline_and_description(client, db):
    token = _complete_survey_real(client, approach='1', scope='1')  # -> entrepreneur; accountant is a non-selected cell
    body = client.get(f'/survey/{token}/result').get_data(as_text=True)

    accountant_tag = next(tag for tag in _open_tags(body) if 'The Accountant' in tag)
    assert 'data-bs-title="The Accountant"' in accountant_tag

    content = _cell_content_attr(accountant_tag, 'data-bs-content')
    assert 'You are the evidence!' in content
    assert 'creating insight into real impact' in content
    assert '&#10;&#10;' in content
    # Tagline must come before the description, separated by the blank line.
    tagline_index = content.index('You are the evidence!')
    separator_index = content.index('&#10;&#10;')
    description_index = content.index('creating insight into real impact')
    assert tagline_index < separator_index < description_index


# ---------------------------------------------------------------------------
# 4. Audience-aware body
# ---------------------------------------------------------------------------

def test_popover_body_is_audience_aware_on_the_organisation_track(client, db):
    token = _complete_survey_real(client, approach='1', scope='1', audience_index=ORGANISATION)
    body = client.get(f'/survey/{token}/result').get_data(as_text=True)

    accountant_tag = next(tag for tag in _open_tags(body) if 'The Accountant' in tag)
    content = _cell_content_attr(accountant_tag, 'data-bs-content')
    assert 'so the organisation knows' in content  # description_organisation wording
    # The individual-register wording for the same sentence must not appear
    # anywhere on the page — every popover on the org track resolves through
    # the same audience-aware macro.
    assert 'so an organisation knows' not in body


# ---------------------------------------------------------------------------
# 5. Escaping
# ---------------------------------------------------------------------------

def test_popover_content_attribute_is_escaped(client, db):
    token = _complete_survey_real(client, approach='1', scope='1')
    body = client.get(f'/survey/{token}/result').get_data(as_text=True)

    contents = [
        _cell_content_attr(tag, 'data-bs-content')
        for tag in _open_tags(body) if 'data-bs-toggle="popover"' in tag
    ]
    assert any('&#39;' in c for c in contents)
    assert all('<' not in c for c in contents)


# ---------------------------------------------------------------------------
# 6. Persona with no tagline/description gets no popover
# ---------------------------------------------------------------------------

def test_persona_with_no_tagline_or_description_renders_no_popover(app):
    html = _render_grid(app)  # must not raise

    assert 'data-bs-toggle="popover"' not in html
    assert 'tabindex="0"' not in html
    cells = _cells(html)
    assert len(cells) == 9


# ---------------------------------------------------------------------------
# 7. Init script
# ---------------------------------------------------------------------------

def test_result_page_includes_the_popover_init_script(client, db):
    token = _complete_survey_real(client, approach='1', scope='1')
    body = client.get(f'/survey/{token}/result').get_data(as_text=True)

    assert re.search(r'<script nonce="[^"]+"', body)
    assert 'new bootstrap.Popover' in body
    assert "container: 'body'" in body
    assert "customClass: 'persona-popover'" in body
    assert "'hover focus'" in body
    assert 'html: true' not in body
    assert 'sanitize: false' not in body


# ---------------------------------------------------------------------------
# 8. No init script when there is no grid
# ---------------------------------------------------------------------------

def test_no_init_script_or_popover_attributes_when_survey_has_no_grid(client, db):
    client.application.config['SURVEY_PATH'] = SURVEY_MIN_PATH
    clear_survey_cache()

    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'q_single': '0'})
    client.post(f'/survey/{token}/step/2', data={'q_multi': []})
    client.post(f'/survey/{token}/step/3', data={'q_spectrum': '0'})
    client.post(f'/survey/{token}/step/4', data={'q_short_text': ''})

    body = client.get(f'/survey/{token}/result').get_data(as_text=True)
    assert 'bootstrap.Popover' not in body
    assert 'data-bs-toggle="popover"' not in body


# ---------------------------------------------------------------------------
# 9. theme.css
# ---------------------------------------------------------------------------

def _normalised_css():
    with open(THEME_CSS_PATH, encoding='utf-8') as f:
        raw = f.read()
    return re.sub(r'\s+', ' ', raw)


def test_theme_css_defines_the_popover_rules_and_mobile_breakpoint_still_last_block():
    css = _normalised_css()

    assert re.search(r'\.grid-cell--result:focus-visible\s*\{[^}]*outline[^}]*\}', css)
    assert re.search(r'\.persona-popover\s*\{[^}]*--bs-popover-max-width[^}]*\}', css)
    assert 'white-space: pre-line' in css

    assert css.count('@media (max-width: 767.98px)') == 1
    match = re.search(r'@media \(max-width: 767\.98px\) \{(.*)\} \}\s*$', css, re.DOTALL)
    assert match, 'mobile breakpoint is no longer the last block in theme.css'
