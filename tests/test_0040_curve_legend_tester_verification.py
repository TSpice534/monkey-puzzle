"""Tester-stage verification for backlog #0040 (innovation-curve band-name
labels moved from in-SVG `<text>` into an HTML `<ul class="curve-legend">`
legend below the chart).

This file closes gaps not already covered by the coder's own additions in
`tests/test_sharing.py` and `tests/test_innovation_curve_visualisation_verification.py`:

  1. The `{% if innovation.bands %}` guard on `_result_innovation.html` is
     exercised *directly* against the partial (not only indirectly via the
     PDF template) with a hand-built `innovation` dict that has no `bands`
     key — confirms the guard is real Jinja behaviour, not just present in
     source, and that omitting `bands` never raises.
  2. `pdf/result.html` renders the legend correctly when `bands` *is*
     present (the coder's own PDF test only covers the bands-absent case).
  3. The current band's indicator — `fw-bold` on its `<li>` *and* a
     visually-hidden "(your band)" suffix — is present in real rendered
     markup, scoped to the correct `<li>`, and absent from every other
     band's `<li>`.
  4. A real `/survey/<token>/result` page render contains zero `<text`
     elements anywhere inside the innovation-curve `<svg>` (not just the
     `render_innovation_curve_svg` unit test in `test_sharing.py`).

No headless-browser/Playwright tooling is set up for this project (checked:
`playwright` is not importable in `.venv`, and no reference to it exists
anywhere in the repo) — visual/pixel-level legibility at a ~390px viewport
is therefore NOT verified here. That remains a manual/visual gap, recorded
in `.pipeline/test-results.md`.
"""
import os
import re

import pytest
from flask import render_template

from app.models import Submission
from app.survey.charts import render_innovation_curve_svg
from app.survey.loader import clear_survey_cache, load_survey

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


def _real_bands():
    survey = load_survey(REAL_SURVEY_PATH)
    return survey['innovation_curve']['bands']


def _start_new(client):
    response = client.get('/survey/start')
    assert response.status_code == 302
    return response.headers['Location'].split('/survey/')[1].split('/step/')[0]


def _complete_survey(client, motivation='4', ambition='4', space_to_progress='4', approach='0', scope='0'):
    """Walk all 11 real-survey steps to completion (mirrors the established
    helper in test_innovation_curve_visualisation_verification.py)."""
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
    client.post(f'/survey/{token}/step/{STEP_MOTIVATION}',
                data={} if motivation is None else {'motivation': motivation})
    client.post(f'/survey/{token}/step/{STEP_AMBITION}',
                data={} if ambition is None else {'ambition': ambition})
    client.post(f'/survey/{token}/step/{STEP_SPACE_TO_PROGRESS}',
                data={} if space_to_progress is None else {'space_to_progress': space_to_progress})
    client.post(f'/survey/{token}/step/{STEP_NEED_MOST}', data={'need_most': '0'})
    client.post(f'/survey/{token}/step/{STEP_HAVE_ENOUGH}', data={'have_enough': '0'})
    client.post(f'/survey/{token}/step/{STEP_PROFILE}', data={'profile_approach': approach, 'profile_scope': scope})
    client.post(f'/survey/{token}/step/{STEP_TOPICS}', data={'topics': ['0', '1', '2']})
    client.post(f'/survey/{token}/step/{STEP_SUPPORT_TYPE}', data={'support_type': '0'})
    client.post(f'/survey/{token}/step/{STEP_TARGET_GROUPS}', data={'target_groups': '0'})
    client.post(f'/survey/{token}/step/{STEP_WHY_REASON}', data={'why_reason': 'Because it matters.'})
    return token


# ---------------------------------------------------------------------------
# 1. The `{% if innovation.bands %}` guard, exercised directly on the
#    partial itself (not only indirectly via the PDF template).
# ---------------------------------------------------------------------------

def test_result_innovation_partial_renders_without_legend_when_bands_key_absent(app):
    """A hand-built `innovation` dict with no 'bands' key (the shape used by
    pre-#0040 callers / other tests) must render the partial cleanly: no
    exception, no legend markup, everything else (band name, colour bar,
    tagline, description) intact."""
    bands = _real_bands()
    late_majority = next(b for b in bands if b['name'] == 'Late Majority')
    innovation = {
        'band': 'Late Majority', 'score': 5, 'colour': late_majority['colour'],
        'tagline': late_majority['tagline'], 'description': late_majority['description'],
        'curve_svg': render_innovation_curve_svg(5, bands),
        # deliberately no 'bands' key
    }

    with app.app_context():
        html = render_template('survey/_result_innovation.html', innovation=innovation)

    assert '<ul class="curve-legend' not in html
    assert 'curve-legend' not in html
    assert 'Late Majority' in html
    assert late_majority['tagline'] in html


def test_result_innovation_partial_renders_without_legend_when_bands_is_empty_list(app):
    """`bands: []` is falsy in Jinja too — same guard, belt-and-braces."""
    bands = _real_bands()
    late_majority = next(b for b in bands if b['name'] == 'Late Majority')
    innovation = {
        'band': 'Late Majority', 'score': 5, 'colour': late_majority['colour'],
        'tagline': late_majority['tagline'], 'description': late_majority['description'],
        'curve_svg': render_innovation_curve_svg(5, bands),
        'bands': [],
    }

    with app.app_context():
        html = render_template('survey/_result_innovation.html', innovation=innovation)

    assert 'curve-legend' not in html


def test_result_innovation_partial_renders_legend_when_bands_present(app):
    """Positive counterpart: with a real 'bands' list, the legend markup
    actually appears (guard doesn't accidentally suppress the happy path)."""
    bands = _real_bands()
    late_majority = next(b for b in bands if b['name'] == 'Late Majority')
    innovation = {
        'band': 'Late Majority', 'score': 5, 'colour': late_majority['colour'],
        'tagline': late_majority['tagline'], 'description': late_majority['description'],
        'curve_svg': render_innovation_curve_svg(5, bands),
        'bands': [
            {'name': b['name'], 'colour': b['colour'], 'is_current': b['name'] == 'Late Majority'}
            for b in sorted(bands, key=lambda b: b['min'], reverse=True)
        ],
    }

    with app.app_context():
        html = render_template('survey/_result_innovation.html', innovation=innovation)

    assert '<ul class="curve-legend' in html
    for b in bands:
        assert b['name'] in html


# ---------------------------------------------------------------------------
# 2. PDF template with `bands` PRESENT — the coder's own PDF test only
#    covers the bands-ABSENT case.
# ---------------------------------------------------------------------------

def test_pdf_template_renders_curve_legend_when_bands_present(app):
    bands = _real_bands()
    innovators = next(b for b in bands if b['name'] == 'Innovators')
    innovation = {
        'band': 'Innovators', 'score': 15, 'colour': innovators['colour'],
        'tagline': innovators['tagline'], 'description': innovators['description'],
        'curve_svg': render_innovation_curve_svg(15, bands),
        'bands': [
            {'name': b['name'], 'colour': b['colour'], 'is_current': b['name'] == 'Innovators'}
            for b in sorted(bands, key=lambda b: b['min'], reverse=True)
        ],
    }
    persona = {
        'name': 'The Accountant', 'tagline': 't', 'description': 'd',
        'natural_allies': [], 'friends': [], 'necessity': [], 'case_studies': [], 'resources': [],
    }

    with app.app_context():
        html = render_template(
            'pdf/result.html', persona=persona, personas={'accountant': persona},
            innovation=innovation, audience=None,
        )

    assert '<ul class="curve-legend' in html
    for b in bands:
        assert b['name'] in html
    # Exactly one band ('Innovators') is current -> exactly one bolded item.
    assert html.count('fw-bold') == 1
    assert 'curve-legend-swatch' in html


# ---------------------------------------------------------------------------
# 3. Current-band indicator: fw-bold + visually-hidden "(your band)" text,
#    actually rendered, scoped to the right <li>, absent from the others.
# ---------------------------------------------------------------------------

def test_current_band_legend_item_is_bold_with_visually_hidden_indicator_others_are_not(app):
    bands = _real_bands()
    current_name = 'Early Majority'
    current = next(b for b in bands if b['name'] == current_name)
    innovation = {
        'band': current_name, 'score': 7, 'colour': current['colour'],
        'tagline': current['tagline'], 'description': current['description'],
        'curve_svg': render_innovation_curve_svg(7, bands),
        'bands': [
            {'name': b['name'], 'colour': b['colour'], 'is_current': b['name'] == current_name}
            for b in sorted(bands, key=lambda b: b['min'], reverse=True)
        ],
    }

    with app.app_context():
        html = render_template('survey/_result_innovation.html', innovation=innovation)

    # Extract each <li>...</li> in the legend and check exactly one carries
    # both the bold class and the visually-hidden suffix, and it's the
    # current band's.
    li_items = re.findall(r'<li class="[^"]*">.*?</li>', html, re.DOTALL)
    assert len(li_items) == len(bands), 'expected one <li> per band in the legend'

    bold_items = [li for li in li_items if 'fw-bold' in li]
    assert len(bold_items) == 1
    assert current_name in bold_items[0]
    assert 'visually-hidden' in bold_items[0]
    assert '(your band)' in bold_items[0]

    non_bold_items = [li for li in li_items if li not in bold_items]
    assert len(non_bold_items) == len(bands) - 1
    for li in non_bold_items:
        assert 'visually-hidden' not in li
        assert '(your band)' not in li


def test_real_result_page_bold_legend_item_carries_visually_hidden_text(client, db):
    """Same check end-to-end through the real route/submission, not just a
    hand-built context."""
    token = _complete_survey(client)
    submission = db.session.query(Submission).filter_by(token=token).one()

    body = client.get(f'/survey/{token}/result').get_data(as_text=True)
    li_items = re.findall(r'<li class="[^"]*">.*?</li>', body, re.DOTALL)
    curve_legend_items = [li for li in li_items if any(b['name'] in li for b in _real_bands())]
    bold_items = [li for li in curve_legend_items if 'fw-bold' in li]

    assert len(bold_items) == 1
    assert submission.innovation_band in bold_items[0]
    assert 'visually-hidden' in bold_items[0]
    assert '(your band)' in bold_items[0]


# ---------------------------------------------------------------------------
# 4. No `<text` element anywhere in a REAL rendered result page's chart SVG
#    (spot-check through the actual route, not just the charts.py unit test).
# ---------------------------------------------------------------------------

def test_real_result_page_chart_svg_contains_no_text_elements(client, db):
    token = _complete_survey(client)
    body = client.get(f'/survey/{token}/result').get_data(as_text=True)

    match = re.search(r'<svg[^>]*aria-label="Innovation curve[^>]*>.*?</svg>', body, re.DOTALL)
    assert match, 'innovation curve <svg> not found in rendered result page'
    svg = match.group(0)

    assert '<text' not in svg
    # The bars themselves are still there — this isn't just an empty chart.
    assert svg.count('<rect') >= 1
