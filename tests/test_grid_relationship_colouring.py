"""Independent tester verification for backlog #0031 (colour-code Natural
Allies/Friends/Necessities on the result-page persona grid).

Two areas the coder flagged for close attention:

  1. The Jinja class-concatenation chain building each cell's classes in
     `app/templates/survey/_result_grid.html` — a single synthetic 3x3 grid
     below (`_render_grid`) exercises every combination in one render: no
     relationship, each single relationship, all three two-way overlaps, the
     three-way overlap, and the selected cell (which must get no relationship
     class even though it lists itself as its own ally — the `is_selected`
     short-circuit guard).
  2. The three-way overlap has no real data in `content/survey.yaml` today
     (confirmed by grepping every persona's natural_allies/friends/necessity
     below) — `test_synthetic_three_way_overlap_renders_all_three_classes_and_the_full_label`
     covers it via the synthetic fixture, and
     `test_theme_css_defines_the_three_way_gradient_rule` sanity-checks the
     CSS rule itself exists with the documented 33.33%/66.66% stops, since
     neither can be exercised end-to-end through the real survey.

Real-data e2e coverage (inventor/cooperator overlap, entrepreneur's
all-three-categories legend, survey_grid.yaml's no-relationship-data fixture)
complements the synthetic template-level tests rather than duplicating them.
"""
import os
import re

import pytest
from flask import render_template

from app.models import Submission
from app.survey.loader import clear_survey_cache

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_SURVEY_PATH = os.path.join(REPO_ROOT, 'content', 'survey.yaml')
GRID_FIXTURE_PATH = os.path.join(REPO_ROOT, 'tests', 'fixtures', 'survey_grid.yaml')
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


# ---------------------------------------------------------------------------
# Template-level synthetic grid — full control over every combination
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
    """3x3 layout (x, y): p00=ally-only, p10=ally+necessity, p20=necessity-only,
    p01=friend-only, p11=SELECTED (the classified persona; self-referencing to
    exercise the selected-cell guard), p21=ally+friend+necessity (triple),
    p02=no relation, p12=friend+necessity, p22=ally+friend."""
    ids = [f'p{x}{y}' for y in [0, 1, 2] for x in [0, 1, 2]]
    personas = {pid: {'id': pid, 'name': f'Persona {pid}'} for pid in ids}
    personas['p11'].update({
        'natural_allies': ['p00', 'p10', 'p21', 'p22', 'p11'],  # self-reference, must be ignored
        'friends': ['p01', 'p12', 'p21', 'p22'],
        'necessity': ['p02', 'p10', 'p12', 'p21'],
    })
    return personas


def _render_grid(app, persona_id='p11', grid_selected=(1, 1), personas=None, persona=None):
    personas = personas if personas is not None else _synthetic_personas()
    persona = persona if persona is not None else personas[persona_id]
    with app.app_context():
        return render_template(
            'survey/_result_grid.html',
            grid_question=_grid_question(),
            grid_selected=list(grid_selected) if grid_selected is not None else None,
            personas=personas,
            persona=persona,
        )


CELL_RE = re.compile(r'<div class="(grid-cell grid-cell--result[^"]*)">(.*?)</div>', re.DOTALL)


def _cells(html):
    """Cells in template render order: y in [2,1,0], x in [0,1,2] — i.e.
    p02, p12, p22, p01, p11, p21, p00, p10, p20."""
    return CELL_RE.findall(html)


def test_synthetic_grid_every_class_combination_is_exact(app):
    html = _render_grid(app)
    cells = _cells(html)
    assert len(cells) == 9

    by_id = dict(zip(
        ['p02', 'p12', 'p22', 'p01', 'p11', 'p21', 'p00', 'p10', 'p20'],
        cells,
    ))

    assert by_id['p00'][0] == 'grid-cell grid-cell--result grid-cell--related grid-cell--ally'
    assert by_id['p01'][0] == 'grid-cell grid-cell--result grid-cell--related grid-cell--friend'
    assert by_id['p02'][0] == 'grid-cell grid-cell--result grid-cell--related grid-cell--necessity'
    assert by_id['p10'][0] == (
        'grid-cell grid-cell--result grid-cell--related grid-cell--ally grid-cell--necessity'
    )
    assert by_id['p12'][0] == (
        'grid-cell grid-cell--result grid-cell--related grid-cell--friend grid-cell--necessity'
    )
    assert by_id['p22'][0] == (
        'grid-cell grid-cell--result grid-cell--related grid-cell--ally grid-cell--friend'
    )
    assert by_id['p20'][0] == 'grid-cell grid-cell--result grid-cell--muted'
    # The selected cell: no relationship class even though p11 lists itself
    # as its own natural ally in the fixture above (guard against a future
    # regression relying on CSS ordering instead of the is_selected short-circuit).
    assert by_id['p11'][0] == 'grid-cell grid-cell--result grid-cell--selected'


def test_synthetic_three_way_overlap_renders_all_three_classes_and_the_full_label(app):
    html = _render_grid(app)
    cells = _cells(html)
    by_id = dict(zip(
        ['p02', 'p12', 'p22', 'p01', 'p11', 'p21', 'p00', 'p10', 'p20'],
        cells,
    ))
    triple_class, triple_body = by_id['p21']
    assert triple_class == (
        'grid-cell grid-cell--result grid-cell--related '
        'grid-cell--ally grid-cell--friend grid-cell--necessity'
    )
    assert '<span class="visually-hidden">Natural ally, Friend, Necessity</span>' in triple_body


def test_synthetic_visually_hidden_labels_match_each_cell_relationship(app):
    html = _render_grid(app)
    cells = _cells(html)
    by_id = dict(zip(
        ['p02', 'p12', 'p22', 'p01', 'p11', 'p21', 'p00', 'p10', 'p20'],
        cells,
    ))
    assert '<span class="visually-hidden">Natural ally</span>' in by_id['p00'][1]
    assert '<span class="visually-hidden">Friend</span>' in by_id['p01'][1]
    assert '<span class="visually-hidden">Necessity</span>' in by_id['p02'][1]
    assert '<span class="visually-hidden">Natural ally, Necessity</span>' in by_id['p10'][1]
    assert '<span class="visually-hidden">Friend, Necessity</span>' in by_id['p12'][1]
    assert '<span class="visually-hidden">Natural ally, Friend</span>' in by_id['p22'][1]
    # No relationship => no hidden label at all.
    assert 'visually-hidden' not in by_id['p20'][1]
    # Selected cell => no relationship label either, even though it's self-referenced.
    assert 'visually-hidden' not in by_id['p11'][1]


def test_synthetic_grid_legend_lists_all_three_categories_and_the_both_note(app):
    html = _render_grid(app)
    assert 'grid-legend' in html
    assert 'Natural Allies' in html
    assert 'Friends' in html
    assert 'Necessities' in html
    assert 'A cell showing two colours is both.' in html


# ---------------------------------------------------------------------------
# Edge cases named in spec.md
# ---------------------------------------------------------------------------

def test_persona_with_empty_relationship_lists_renders_no_legend_and_all_muted(app):
    personas = _synthetic_personas()
    personas['p11'].update({'natural_allies': [], 'friends': [], 'necessity': []})
    html = _render_grid(app, personas=personas)

    assert 'grid-legend' not in html
    cells = _cells(html)
    non_selected = [c for c in cells if 'grid-cell--selected' not in c[0]]
    assert len(non_selected) == 8
    assert all(c[0] == 'grid-cell grid-cell--result grid-cell--muted' for c in non_selected)


def test_persona_dict_missing_relationship_keys_entirely_does_not_raise(app):
    """Several real tests build persona dicts by hand without natural_allies/
    friends/necessity at all — the `or []` fallback in the template must
    prevent an Undefined error on `in`, and the legend guard must treat a
    missing key as falsy."""
    personas = _synthetic_personas()
    personas['p11'] = {'id': 'p11', 'name': 'Persona p11'}  # no relationship keys at all

    html = _render_grid(app, personas=personas)  # must not raise

    assert 'grid-legend' not in html
    cells = _cells(html)
    non_selected = [c for c in cells if 'grid-cell--selected' not in c[0]]
    assert len(non_selected) == 8
    assert all(c[0] == 'grid-cell grid-cell--result grid-cell--muted' for c in non_selected)


def test_only_one_category_populated_shows_only_that_legend_key_and_no_both_note(app):
    personas = _synthetic_personas()
    personas['p11'].update({'natural_allies': ['p00'], 'friends': [], 'necessity': []})
    html = _render_grid(app, personas=personas)

    assert 'Natural Allies' in html
    assert 'Friends' not in html
    assert 'Necessities' not in html
    assert 'A cell showing two colours is both.' not in html


def test_two_categories_populated_shows_the_both_note(app):
    personas = _synthetic_personas()
    personas['p11'].update({'natural_allies': ['p00'], 'friends': ['p01'], 'necessity': []})
    html = _render_grid(app, personas=personas)

    assert 'Natural Allies' in html
    assert 'Friends' in html
    assert 'Necessities' not in html
    assert 'A cell showing two colours is both.' in html


def test_grid_selected_none_colours_all_nine_cells_normally_with_none_selected(app):
    """Defensive path in `_profile_grid_context` for malformed/missing profile
    answers — no cell should be selected, but relationship colouring still
    applies to all 9 cells, including the (no-longer-guarded) former
    "selected" cell: with is_selected never true, p11's self-reference in its
    own natural_allies list (present in the fixture specifically to exercise
    the guard) now legitimately colours its own cell as an ally, proving the
    guard in the real is_selected=True case is doing real work, not
    coincidentally matching some other reason it stayed uncoloured."""
    html = _render_grid(app, grid_selected=None)

    assert 'grid-cell--selected' not in html
    cells = _cells(html)
    assert len(cells) == 9
    assert all('grid-cell--selected' not in c[0] for c in cells)

    by_id = dict(zip(
        ['p02', 'p12', 'p22', 'p01', 'p11', 'p21', 'p00', 'p10', 'p20'],
        cells,
    ))
    assert by_id['p11'][0] == 'grid-cell grid-cell--result grid-cell--related grid-cell--ally'


def test_grid_question_none_renders_nothing():
    """Surveys without profile_matrix — the outer guard must render nothing,
    keeping the legend safely inside it too (no context needed at all)."""
    from app import create_app
    from config import Config

    class NoDBConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = 'sqlite://'

    application = create_app(NoDBConfig)
    with application.app_context():
        html = render_template(
            'survey/_result_grid.html',
            grid_question=None, grid_selected=None, personas={}, persona={},
        )
    assert html.strip() == ''


# ---------------------------------------------------------------------------
# CSS sanity check — the three-way gradient rule is unreachable via the real
# survey today (no persona has a 3-way overlap in content/survey.yaml), so it
# can only be verified by parsing theme.css directly, mirroring the existing
# style of test_mobile_responsive_layout.py.
# ---------------------------------------------------------------------------

def _normalised_css():
    with open(THEME_CSS_PATH, encoding='utf-8') as f:
        raw = f.read()
    return re.sub(r'\s+', ' ', raw)


def test_theme_css_defines_the_three_way_gradient_rule():
    css = _normalised_css()
    match = re.search(
        r'\.grid-cell--ally\.grid-cell--friend\.grid-cell--necessity\s*\{([^}]*)\}', css,
    )
    assert match, 'three-way overlap CSS rule not found'
    body = match.group(1)
    assert '33.33%' in body
    assert '66.66%' in body
    assert 'linear-gradient(135deg' in body


def test_theme_css_defines_all_three_two_way_gradient_rules():
    css = _normalised_css()
    for pair in [
        '.grid-cell--ally.grid-cell--friend',
        '.grid-cell--ally.grid-cell--necessity',
        '.grid-cell--friend.grid-cell--necessity',
    ]:
        escaped = re.escape(pair)
        # Match the two-way rule specifically (not the three-way selector,
        # which also starts with these tokens) — the two-way selector is
        # followed directly by ` {`.
        match = re.search(escaped + r'\s*\{([^}]*)\}', css)
        assert match, f'{pair} CSS rule not found'
        assert 'linear-gradient(135deg' in match.group(1)


def test_theme_css_mobile_breakpoint_still_last_block_with_grid_legend_rules():
    """Regression guard named by the planner: the coder's mobile tweaks for
    .grid-legend/.grid-legend-swatch must live inside the existing (and only)
    @media block, which must still be the last thing in the file."""
    css = _normalised_css()
    assert css.count('@media (max-width: 767.98px)') == 1
    match = re.search(r'@media \(max-width: 767\.98px\) \{(.*)\} \}\s*$', css, re.DOTALL)
    assert match, 'mobile breakpoint is no longer the last block in theme.css'
    media_block = match.group(1)
    assert '.grid-legend' in media_block
    assert '.grid-legend-swatch' in media_block


# ---------------------------------------------------------------------------
# Real-data e2e — content/survey.yaml's actual overlap cases
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


def _complete_survey_real(client, approach, scope):
    client.application.config['SURVEY_PATH'] = REAL_SURVEY_PATH
    clear_survey_cache()
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
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


def test_inventor_real_overlap_architect_cell_is_ally_and_necessity(client, db):
    """inventor (approach=2, scope=0): natural_allies=[architect],
    friends=[connector], necessity=[architect] — architect must render as a
    genuine two-way ally+necessity overlap; connector as friend-only."""
    token = _complete_survey_real(client, approach='2', scope='0')
    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.persona_id == 'inventor'

    body = client.get(f'/survey/{token}/result').get_data(as_text=True)
    cells = _cells(body)
    assert len(cells) == 9

    architect_cell = next(c for c in cells if 'Architect' in c[1])
    assert 'grid-cell--related' in architect_cell[0]
    assert 'grid-cell--ally' in architect_cell[0]
    assert 'grid-cell--necessity' in architect_cell[0]
    assert 'grid-cell--friend' not in architect_cell[0]
    assert 'Natural ally, Necessity' in architect_cell[1]

    connector_cell = next(c for c in cells if 'Connector' in c[1])
    assert connector_cell[0] == 'grid-cell grid-cell--result grid-cell--related grid-cell--friend'

    # 3 relationship-bearing categories all populated -> full legend + note.
    assert 'Natural Allies' in body
    assert 'Friends' in body
    assert 'Necessities' in body
    assert 'A cell showing two colours is both.' in body


def test_cooperator_real_overlap_connector_cell_is_ally_and_necessity(client, db):
    """cooperator (approach=2, scope=2): natural_allies=[connector],
    friends=[communicator], necessity=[connector] — the spec's other named
    overlap case."""
    token = _complete_survey_real(client, approach='2', scope='2')
    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.persona_id == 'cooperator'

    body = client.get(f'/survey/{token}/result').get_data(as_text=True)
    cells = _cells(body)
    connector_cell = next(c for c in cells if 'Connector' in c[1])
    assert 'grid-cell--ally' in connector_cell[0]
    assert 'grid-cell--necessity' in connector_cell[0]
    assert 'Natural ally, Necessity' in connector_cell[1]


def test_entrepreneur_real_data_has_five_related_three_muted_one_selected(client, db):
    """entrepreneur (approach=1, scope=1): natural_allies=[implementer,
    cooperator], friends=[communicator, architect], necessity=[accountant] —
    5 distinct related cells (no overlaps), 3 muted (inventor, activist,
    connector), 1 selected."""
    token = _complete_survey_real(client, approach='1', scope='1')
    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.persona_id == 'entrepreneur'

    body = client.get(f'/survey/{token}/result').get_data(as_text=True)
    cells = _cells(body)
    assert len(cells) == 9

    selected = [c for c in cells if 'grid-cell--selected' in c[0]]
    related = [c for c in cells if 'grid-cell--related' in c[0]]
    muted = [c for c in cells if 'grid-cell--muted' in c[0]]
    assert len(selected) == 1
    assert len(related) == 5
    assert len(muted) == 3
    # No overlaps for entrepreneur -> every related cell has exactly one
    # rel-category class.
    for cls, _ in related:
        rel_classes = [c for c in cls.split() if c.startswith('grid-cell--') and
                       c not in ('grid-cell--result', 'grid-cell--related')]
        assert len(rel_classes) == 1
    # entrepreneur's three relationship categories (allies/friends/necessity)
    # are all non-empty even though no single *cell* overlaps two of them —
    # the "both" note is keyed off category population, not per-cell overlap
    # (rel_category_count in the template), so it renders here too.
    assert 'A cell showing two colours is both.' in body


def test_survey_without_relationship_data_shows_no_legend_and_leaves_cells_muted(client, db):
    """survey_grid.yaml's personas have no natural_allies/friends/necessity
    keys at all — must not raise, must render no legend, and every
    non-selected cell must stay grid-cell--muted exactly as before this
    feature (backlog #0031 must not regress the pre-existing fixture)."""
    client.application.config['SURVEY_PATH'] = GRID_FIXTURE_PATH
    clear_survey_cache()

    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'respondent_type': str(INDIVIDUAL)})
    client.post(f'/survey/{token}/step/2', data={'q_worded': '0'})
    client.post(f'/survey/{token}/step/3', data={'q_triangle': '0'})
    client.post(f'/survey/{token}/step/4', data={'q_multi_exact': ['0', '1']})
    client.post(f'/survey/{token}/step/5', data={'profile_approach': '0', 'profile_scope': '2'})  # -> activist
    client.post(f'/survey/{token}/step/6', data={'q_multi_range': ['0']})

    body = client.get(f'/survey/{token}/result').get_data(as_text=True)
    assert 'grid-legend' not in body
    cells = _cells(body)
    assert len(cells) == 9
    non_selected = [c for c in cells if 'grid-cell--selected' not in c[0]]
    assert len(non_selected) == 8
    assert all(c[0] == 'grid-cell grid-cell--result grid-cell--muted' for c in non_selected)


# ---------------------------------------------------------------------------
# Failure case — the template deliberately has no defensive validation of
# relationship ids (`cell.persona in (persona.natural_allies or [])` trusts
# every id in natural_allies/friends/necessity references a real persona).
# That trust boundary is enforced upstream by the loader, not the template
# (spec.md, loader.py lines 92-100) — this proves it actually fails loudly
# at load time rather than silently producing a broken/empty grid, which is
# the failure mode this feature's design relies on never reaching the
# template in the first place.
# ---------------------------------------------------------------------------

def test_loader_rejects_a_relationship_referencing_an_unknown_persona_id(tmp_path):
    from app.survey.loader import SurveyConfigError, load_survey

    personas = {
        pid: {'name': f'The {pid.title()}', 'tagline': 'Tagline', 'description': 'Description'}
        for pid in ['accountant', 'implementer', 'inventor', 'architect', 'communicator',
                    'activist', 'connector', 'cooperator', 'entrepreneur']
    }
    # backlog #0031's new colour-coding trusts this field; corrupt it exactly
    # the way a hand-edit to content/survey.yaml could.
    personas['inventor']['natural_allies'] = ['not-a-real-persona-id']
    config = {
        'meta': {'version': 1, 'title': 'Fixture Survey', 'personas_count': 9},
        'personas': personas,
        'questions': [
            {
                'id': 'q_single', 'type': 'single', 'prompt': 'Pick one',
                'dimension': 'roots',
                'options': [
                    {'label': 'Option A', 'weights': {'inventor': 2}},
                    {'label': 'Option B', 'weights': {'accountant': 2}},
                ],
            },
        ],
        'scoring': {
            'method': 'persona_vector',
            'tie_break': list(personas.keys()),
            'equity_modifier': {'enabled': False},
            'rogers_curve': {'enabled': False},
        },
    }
    path = tmp_path / 'survey.yaml'
    import yaml
    path.write_text(yaml.safe_dump(config), encoding='utf-8')

    with pytest.raises(SurveyConfigError):
        load_survey(str(path))
