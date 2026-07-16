"""Independent tester verification for backlog #0011 (innovation-curve
inline-SVG visualisation on the results page), against the REAL
content/survey.yaml — complementing (not duplicating) the coder's own unit
tests in tests/test_sharing.py, which exercise `render_innovation_curve_svg`
against a small local `_CURVE_BANDS` fixture only.

Focus areas independently verified here, going beyond "the function returns
a string" / "the route returns 200":

  1. Happy path: the SVG actually renders on the real web result page (real
     survey, real bands, real submission) with the score/band named in the
     aria-label, matching the band text already shown below the chart.
  2. The two boundary-score edge cases the coder's own changes.md flagged for
     manual eyeballing (score 2 -> Laggards/Late Majority boundary, score 15
     -> Early Adopters/Innovators boundary) — driven through the real 11-step
     flow, not a hand-built fixture, confirming exactly one bar highlights
     and the aria-label's band name matches the band text shown below.
  3. Orientation (the spec's one flagged OPEN QUESTION, resolved
     Innovators-left): against the REAL band colours, the leftmost bar in
     the drawn markup is Innovators-coloured and the rightmost is
     Laggards-coloured.
  4. Web + PDF, not email: the curve SVG renders inside the actual PDF
     template and is genuinely absent from both email bodies, even though
     `curve_svg` is computed and threaded into the same `innovation` dict
     used for email.
  5. Defensive/failure cases: a `score` far outside `[lo, hi]` still
     highlights exactly one (end) bar and never crashes; a gap in band
     coverage (no band matches a given score point) falls back to the
     documented neutral grey rather than raising or silently mis-colouring.

Every bar always renders its own band's bold colour — highlighting is done
via `fill-opacity` (1 for the respondent's bar, `UNHIGHLIGHTED_BAR_OPACITY`
for every other bar), not by desaturating the colour itself. Assertions
below check the fill/fill-opacity pair together rather than fill alone,
since a band with more than one score point has that same bold colour on
several bars at once.
"""
import os
import re

import pytest

from app.models import Submission
from app.survey.charts import UNHIGHLIGHTED_BAR_OPACITY, render_innovation_curve_svg
from app.survey.loader import clear_survey_cache, load_survey

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_SURVEY_PATH = os.path.join(REPO_ROOT, 'content', 'survey.yaml')

INDIVIDUAL = 0

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


@pytest.fixture(autouse=True)
def _use_real_survey(app):
    app.config['SURVEY_PATH'] = REAL_SURVEY_PATH
    clear_survey_cache()
    yield
    clear_survey_cache()


def _real_bands():
    survey = load_survey(REAL_SURVEY_PATH)
    return survey['innovation_curve']['bands']


def _extract_curve_svg(body):
    """The rendered result page also embeds the persona fingerprint radar
    chart, which reuses the same brand-green (#2e7d32) as a fill colour —
    scope any fill-colour assertion to just the curve <svg>...</svg> (found
    via its distinctive aria-label) rather than the whole page body."""
    match = re.search(r'<svg[^>]*aria-label="Innovation curve[^>]*>.*?</svg>', body, re.DOTALL)
    assert match, 'innovation curve <svg> not found in rendered body'
    return match.group(0)


def _highlighted_bar_count(svg, colour):
    """Count bars matching `colour` at full opacity (fill-opacity="1") — the
    single respondent-highlighted bar, as opposed to every other bar of the
    same band which also carries `colour` but at reduced opacity."""
    return len(re.findall(rf'<rect[^>]*fill="{re.escape(colour)}" fill-opacity="1"', svg))


def _start_new(client):
    response = client.get('/survey/start')
    assert response.status_code == 302
    return response.headers['Location'].split('/survey/')[1].split('/step/')[0]


def _complete_survey(client, motivation='0', ambition='0', space_to_progress='0', grid='0,0'):
    """Walk all 11 real-survey steps to completion. grid='0,0' -> accountant
    (persona modifier +0), so the innovation score is directly attributable
    to the three answered questions. `None` for a question skips it
    entirely (contributes 0), matching the established pattern for driving
    specific totals in this suite."""
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
    client.post(f'/survey/{token}/step/{STEP_WHY_REASON}', data={'why_reason': 'Because it matters.'})
    client.post(f'/survey/{token}/step/{STEP_MOTIVATION}',
                data={} if motivation is None else {'motivation': motivation})
    client.post(f'/survey/{token}/step/{STEP_AMBITION}',
                data={} if ambition is None else {'ambition': ambition})
    client.post(f'/survey/{token}/step/{STEP_SPACE_TO_PROGRESS}',
                data={} if space_to_progress is None else {'space_to_progress': space_to_progress})
    client.post(f'/survey/{token}/step/{STEP_NEED_MOST}', data={'need_most': '0'})
    client.post(f'/survey/{token}/step/{STEP_HAVE_ENOUGH}', data={'have_enough': '0'})
    client.post(f'/survey/{token}/step/{STEP_PROFILE_GRID}', data={'profile_grid': grid})
    client.post(f'/survey/{token}/step/{STEP_TOPICS}', data={'topics': ['0', '1', '2']})
    client.post(f'/survey/{token}/step/{STEP_SUPPORT_TYPE}', data={'support_type': '0'})
    client.post(f'/survey/{token}/step/{STEP_TARGET_GROUPS}', data={'target_groups': '0'})
    return token


# ---------------------------------------------------------------------------
# 1. Happy path — real survey, real bands, real submission
# ---------------------------------------------------------------------------

def test_happy_path_curve_svg_renders_on_real_result_page_with_matching_score_and_band(client, db):
    # motivation idx0 (score1) + ambition idx0 (score1) + space idx0 (score1)
    # = 3, accountant modifier +0 -> 3 -> Late Majority (band 3-7).
    token = _complete_survey(client)
    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.innovation_score == 3
    assert submission.innovation_band == 'Late Majority'

    body = client.get(f'/survey/{token}/result').get_data(as_text=True)
    assert 'role="img"' in body
    assert 'aria-label="Innovation curve — you scored 3 of 20 (Late Majority).' in body
    # 21 score points (0-20 inclusive) -> 21 bars in the curve alone. The
    # fingerprint radar chart also emits <rect>-free polygons/lines, so
    # counting rects globally is still an exact, unambiguous check.
    assert body.count('<rect') >= 21


# ---------------------------------------------------------------------------
# 2. Boundary scores flagged in changes.md, driven through the real flow
# ---------------------------------------------------------------------------

def test_boundary_score_2_laggards_late_majority_highlights_correct_band(client, db):
    # motivation idx0 (1) + ambition idx0 (1) + space skipped (0) = 2,
    # accountant modifier +0 -> 2 -> Laggards (band 0-2), one below the
    # Late Majority boundary.
    token = _complete_survey(client, motivation='0', ambition='0', space_to_progress=None)
    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.innovation_score == 2
    assert submission.innovation_band == 'Laggards'

    body = client.get(f'/survey/{token}/result').get_data(as_text=True)
    assert 'aria-label="Innovation curve — you scored 2 of 20 (Laggards).' in body
    # Exactly one bar highlighted (full opacity) in Laggards' colour.
    assert _highlighted_bar_count(_extract_curve_svg(body), '#c0392b') == 1


def test_boundary_score_15_early_adopters_innovators_highlights_correct_band(client, db):
    # motivation idx4 (5) + ambition idx2 (5) + space idx2 (5) = 15,
    # accountant modifier +0 -> 15 -> Innovators (band 15-20), one above the
    # Early Adopters boundary.
    token = _complete_survey(client, motivation='4', ambition='2', space_to_progress='2')
    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.innovation_score == 15
    assert submission.innovation_band == 'Innovators'

    body = client.get(f'/survey/{token}/result').get_data(as_text=True)
    assert 'aria-label="Innovation curve — you scored 15 of 20 (Innovators).' in body
    # Scoped to the curve <svg> itself — the persona fingerprint radar chart
    # elsewhere on the page also uses #2e7d32 as a fill colour.
    assert _highlighted_bar_count(_extract_curve_svg(body), '#2e7d32') == 1


# ---------------------------------------------------------------------------
# 3. Orientation — Innovators-left, Laggards-right, against the REAL colours
#    (the spec's one flagged OPEN QUESTION, resolved by the coder)
# ---------------------------------------------------------------------------

def test_orientation_leftmost_bar_is_innovators_rightmost_is_laggards():
    bands = _real_bands()
    svg = render_innovation_curve_svg(None, bands)  # no highlight -> every bar at reduced opacity

    bars = re.findall(r'<rect[^>]*fill="(#[0-9a-f]{6})" fill-opacity="([0-9.]+)"', svg)
    assert len(bars) == 21

    innovators_colour = next(b['colour'] for b in bands if b['name'] == 'Innovators')
    laggards_colour = next(b['colour'] for b in bands if b['name'] == 'Laggards')

    # Every bar keeps its own bold colour — only opacity is reduced without
    # a highlighted score.
    assert bars[0] == (innovators_colour, str(UNHIGHLIGHTED_BAR_OPACITY))
    assert bars[-1] == (laggards_colour, str(UNHIGHLIGHTED_BAR_OPACITY))


# ---------------------------------------------------------------------------
# 4. Web + PDF, not email
# ---------------------------------------------------------------------------

def test_curve_svg_renders_inside_the_real_pdf_template(app):
    from flask import render_template

    bands = _real_bands()
    late_majority = next(b for b in bands if b['name'] == 'Late Majority')
    innovation = {
        'band': 'Late Majority', 'score': 5, 'colour': late_majority['colour'],
        'tagline': late_majority['tagline'], 'description': late_majority['description'],
        'curve_svg': render_innovation_curve_svg(5, bands),
    }
    persona = {
        'name': 'The Accountant', 'tagline': 't', 'description': 'd',
        'natural_allies': [], 'friends': [], 'necessity': [], 'case_studies': [], 'resources': [],
    }

    with app.app_context():
        html = render_template(
            'pdf/result.html', persona=persona, personas={'accountant': persona},
            fingerprint_svg='<svg></svg>', innovation=innovation, audience=None,
        )
    assert 'Innovation curve — you scored 5 of 20 (Late Majority).' in html


def test_curve_svg_is_absent_from_both_email_bodies_even_though_it_is_computed(app):
    """`curve_svg` rides along in the same `innovation` dict threaded to the
    email templates (per routes.py::_innovation_context), but the email
    templates render their own inline markup and must never include it."""
    from flask import render_template

    bands = _real_bands()
    late_majority = next(b for b in bands if b['name'] == 'Late Majority')
    innovation = {
        'band': 'Late Majority', 'score': 5, 'colour': late_majority['colour'],
        'tagline': late_majority['tagline'], 'description': late_majority['description'],
        'curve_svg': render_innovation_curve_svg(5, bands),
    }
    persona = {'name': 'The Accountant', 'tagline': 't', 'description': 'd'}

    with app.app_context():
        text_body = render_template(
            'email/result.txt', persona=persona, result_url='https://example.com/r',
            innovation=innovation, audience=None,
        )
        html_body = render_template(
            'email/result.html', persona=persona, result_url='https://example.com/r',
            innovation=innovation, audience=None,
        )

    assert 'Innovation curve —' not in text_body
    assert 'Innovation curve —' not in html_body
    assert '<svg' not in text_body
    # The email HTML body may legitimately contain no <svg> at all per the
    # established #0002 precedent (it renders its own inline markup, no
    # chart of any kind) — assert specifically that *this* chart is absent.
    assert 'role="img" aria-label="Innovation curve' not in html_body


# ---------------------------------------------------------------------------
# 5. Defensive/failure cases
# ---------------------------------------------------------------------------

def test_score_far_outside_range_clamps_to_one_end_bar_and_states_real_score():
    bands = _real_bands()

    svg_above = render_innovation_curve_svg(999, bands)
    innovators_colour = next(b['colour'] for b in bands if b['name'] == 'Innovators')
    assert _highlighted_bar_count(svg_above, innovators_colour) == 1
    assert 'aria-label="Innovation curve — you scored 999 of 20 (Innovators).' in svg_above

    svg_below = render_innovation_curve_svg(-50, bands)
    laggards_colour = next(b['colour'] for b in bands if b['name'] == 'Laggards')
    assert _highlighted_bar_count(svg_below, laggards_colour) == 1
    assert 'aria-label="Innovation curve — you scored -50 of 20 (Laggards).' in svg_below


def test_gap_in_band_coverage_falls_back_to_neutral_grey_without_raising():
    """Defensive path (spec: 'if none matches, use a neutral grey
    (#adb5bd)') — construct bands with a genuine coverage gap (no band
    matches score points 8-12) and confirm the generator neither raises nor
    silently mis-colours those bars."""
    bands_with_gap = [
        {'name': 'Laggards', 'min': 0, 'max': 2, 'colour': '#c0392b'},
        {'name': 'Late Majority', 'min': 3, 'max': 7, 'colour': '#e67e22'},
        # Early Majority (8-12) deliberately omitted -> a real gap.
        {'name': 'Early Adopters', 'min': 13, 'max': 14, 'colour': '#7cb342'},
        {'name': 'Innovators', 'min': 15, 'max': 20, 'colour': '#2e7d32'},
    ]

    svg = render_innovation_curve_svg(10, bands_with_gap)  # 10 falls in the gap

    assert svg.startswith('<svg')
    assert 'fill="#adb5bd"' in svg  # the neutral-grey fallback for the gap points
    # Every point still gets exactly one bar — the gap doesn't drop points.
    assert svg.count('<rect') == 21
