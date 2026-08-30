"""Independent tester verification for backlog #0029 (mobile-responsive
spectrum/triangle/grid layout + the innovation-curve label-collision fix's
supporting CSS) — complementing (not duplicating) the coder's own unit tests
in tests/test_sharing.py, which exercise `render_innovation_curve_svg`'s
label-layout algorithm directly against small band fixtures.

Focus areas independently verified here:

  1. `app/static/css/theme.css` actually carries the one-and-only mobile
     breakpoint (767.98px, Bootstrap 5's `md` boundary) with the
     `.spectrum-widget` column-stack rule inside it, plus the
     `.innovation-curve svg` sizing rule that keeps the fixed-width/height
     SVG from overflowing a narrow card.
  2. The real survey's result page actually renders the two new hook
     classes (`innovation-curve`, `table-responsive`) that this CSS targets
     — a passing CSS-file assertion alone would not catch a hook class that
     never made it into the template.
  3. `theme.css` has no comment that closes early. This reproduces a real
     incident from this backlog: a comment reading "...col-sm-*/col-md-*..."
     contains a literal `*/` mid-sentence, which every real CSS parser
     treats as the comment's actual end — everything after it (here, the
     entire mobile breakpoint) silently collapses into one invalid rule and
     gets discarded, while the raw file text looks completely untouched.
     Substring-presence assertions like the ones below do not catch this;
     only a parser (or an equivalent comment-stripping pass) does.
"""
import os
import re

import pytest

from app.models import Submission
from app.survey.loader import clear_survey_cache, load_survey

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_SURVEY_PATH = os.path.join(REPO_ROOT, 'content', 'survey.yaml')
THEME_CSS_PATH = os.path.join(REPO_ROOT, 'app', 'static', 'css', 'theme.css')

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


def _complete_survey(client, motivation='0', ambition='0', space_to_progress='0', approach='0', scope='0'):
    """Walk all 12 real-survey steps to completion. approach='0', scope='0'
    -> accountant (persona modifier +0), so the innovation score is directly
    attributable to the three answered questions. `None` for a question
    skips it entirely (contributes 0), matching the established pattern for
    driving specific totals in this suite."""
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
# 0. theme.css has no comment that closes early (see module docstring #3)
# ---------------------------------------------------------------------------

def test_theme_css_has_no_premature_comment_close():
    with open(THEME_CSS_PATH, encoding='utf-8') as f:
        raw = f.read()

    # Non-greedy: matches each /* up to the FIRST following */, same as a
    # real CSS tokenizer. Any '*/' left over after stripping every such
    # pair means an earlier comment closed before its intended end.
    stripped = re.sub(r'/\*.*?\*/', '', raw, flags=re.DOTALL)
    assert '*/' not in stripped, (
        "a '*/' remains outside any /* */ pair — a comment earlier in the "
        "file is closing early (e.g. a wildcard pattern like 'col-sm-*/"
        "col-md-*' contains a literal */ mid-sentence). Every real CSS "
        "parser silently discards everything after the true end of that "
        "comment's actual scope, even though the raw file text looks "
        "completely intact — this exact bug has happened once already."
    )


# ---------------------------------------------------------------------------
# 1. theme.css — the mobile breakpoint and the SVG sizing rule
# ---------------------------------------------------------------------------

def _normalised_css():
    with open(THEME_CSS_PATH, encoding='utf-8') as f:
        raw = f.read()
    return re.sub(r'\s+', ' ', raw)


def test_theme_css_has_exactly_one_mobile_breakpoint_stacking_the_spectrum_widget():
    css = _normalised_css()

    assert css.count('@media (max-width: 767.98px)') == 1

    match = re.search(r'@media \(max-width: 767\.98px\) \{(.*)\} \}\s*$', css, re.DOTALL)
    assert match, 'could not isolate the mobile breakpoint block'
    media_block = match.group(1)

    assert re.search(r'\.spectrum-widget\s*\{[^}]*flex-direction:\s*column', media_block)


def test_theme_css_has_innovation_curve_svg_sizing_rule():
    css = _normalised_css()

    match = re.search(r'\.innovation-curve svg\s*\{([^}]*)\}', css)
    assert match, '.innovation-curve svg rule not found'
    rule_body = match.group(1)

    assert 'max-width: 100%' in rule_body
    assert 'height: auto' in rule_body


# ---------------------------------------------------------------------------
# 2. Real result page actually renders the hook classes theme.css targets
# ---------------------------------------------------------------------------

def test_real_result_page_renders_innovation_curve_and_table_responsive_hook_classes(client, db):
    token = _complete_survey(client)
    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.innovation_score is not None

    body = client.get(f'/survey/{token}/result').get_data(as_text=True)
    assert 'class="innovation-curve' in body
    assert 'class="table-responsive"' in body
