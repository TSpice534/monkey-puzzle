"""Backlog #0049: the result page's persona card is the hero (web + PDF).
Email, share card and certificate are untouched."""
import os
import re

import pytest

from app.survey.loader import clear_survey_cache, load_survey

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_SURVEY_PATH = os.path.join(REPO_ROOT, 'content', 'survey.yaml')
SURVEY_GRID_PATH = os.path.join(REPO_ROOT, 'tests', 'fixtures', 'survey_grid.yaml')
THEME_CSS_PATH = os.path.join(REPO_ROOT, 'app', 'static', 'css', 'theme.css')

INNOVATION = {
    'band': 'Innovators', 'score': 18, 'colour': '#2e7d32',
    'tagline': 'You are an Innovator', 'description': 'x',
}


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


def _complete_real_survey(client):
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'respondent_type': '0'})
    client.post(f'/survey/{token}/step/2', data={'motivation': '4'})
    client.post(f'/survey/{token}/step/3', data={'ambition': '4'})
    client.post(f'/survey/{token}/step/4', data={'space_to_progress': '4'})
    client.post(f'/survey/{token}/step/5', data={'need_most': '0'})
    client.post(f'/survey/{token}/step/6', data={'have_enough': '0'})
    client.post(f'/survey/{token}/step/7', data={'profile_approach': '1', 'profile_scope': '1'})
    client.post(f'/survey/{token}/step/8', data={'topics': ['0', '1', '2']})
    client.post(f'/survey/{token}/step/9', data={'support_type': '0'})
    client.post(f'/survey/{token}/step/10', data={'target_groups': '0'})
    final = client.post(f'/survey/{token}/step/11', data={'why_reason': 'Because it matters.'})
    assert final.headers['Location'].endswith(f'/survey/{token}/result')
    return token


@pytest.fixture
def result_body(client):
    token = _complete_real_survey(client)
    response = client.get(f'/survey/{token}/result')
    assert response.status_code == 200
    return response.get_data(as_text=True)


def _css():
    with open(THEME_CSS_PATH, encoding='utf-8') as f:
        return re.sub(r'\s+', ' ', f.read())


def _rule_body(css, selector):
    match = re.search(re.escape(selector) + r' \{([^}]*)\}', css)
    assert match, selector
    return match.group(1)


# 1 ---------------------------------------------------------------------------

def test_result_page_has_hero_markup_in_order(result_body):
    for needle in ('persona-hero', 'persona-hero__head', 'persona-hero__eyebrow',
                   'class="mx-auto result-page"'):
        assert needle in result_body
    icon = result_body.index('persona-icon--card')
    eyebrow = result_body.index('Your sustainable who')
    name = result_body.index('<h1 class="h3 persona-hero__name">')
    tagline = result_body.index('class="lead"')
    assert icon < eyebrow < name < tagline


# 2 ---------------------------------------------------------------------------

def test_hero_heading_contains_only_the_persona_name(result_body):
    match = re.search(r'<h1 class="h3 persona-hero__name">(.*?)</h1>', result_body, re.S)
    assert match
    assert match.group(1).strip() == 'The Entrepreneur'
    assert '<svg' not in match.group(1)
    assert 'persona-icon' not in match.group(1)


# 3 ---------------------------------------------------------------------------

def test_eyebrow_is_not_text_muted(result_body):
    match = re.search(r'<p class="([^"]*persona-hero__eyebrow[^"]*)"', result_body)
    assert match
    assert 'text-muted' not in match.group(1)


# 4 ---------------------------------------------------------------------------

def test_fixture_survey_without_icons_still_renders_hero_without_icon(client):
    client.application.config['SURVEY_PATH'] = SURVEY_GRID_PATH
    clear_survey_cache()
    try:
        token = _start_new(client)
        client.post(f'/survey/{token}/step/1', data={'respondent_type': '0'})
        client.post(f'/survey/{token}/step/2', data={'q_worded': '0'})
        client.post(f'/survey/{token}/step/3', data={'q_triangle': '0'})
        client.post(f'/survey/{token}/step/4', data={'q_multi_exact': ['0', '1']})
        client.post(f'/survey/{token}/step/5', data={'profile_approach': '1', 'profile_scope': '1'})
        client.post(f'/survey/{token}/step/6', data={'q_multi_range': ['0', '1']})
        response = client.get(f'/survey/{token}/result')
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert 'persona-hero' in body
        assert 'persona-icon--card' not in body
    finally:
        client.application.config['SURVEY_PATH'] = REAL_SURVEY_PATH
        clear_survey_cache()


# 5 ---------------------------------------------------------------------------

def test_innovation_card_keeps_its_band_left_border(result_body):
    assert 'border-left: 6px solid' in result_body


# 6 ---------------------------------------------------------------------------

def test_theme_css_hero_rules():
    css = _css()
    assert 'width: 4rem' in _rule_body(css, '.persona-icon--card')
    hero = _rule_body(css, '.persona-hero')
    assert 'var(--selected-tint)' in hero
    assert 'var(--brand-accent)' in hero
    assert '#' not in hero
    assert '.result-page > .card:not(.persona-hero) {' in css
    assert 'box-shadow: none !important' in _rule_body(css, '.result-page > .card:not(.persona-hero)')
    mobile = css[css.index('@media (max-width: 767.98px)'):]
    assert re.search(r'\.persona-hero__head \{[^}]*flex-direction: column', mobile)
    assert css.count('@media (prefers-color-scheme: dark)') == 2


# 7 ---------------------------------------------------------------------------

def test_pdf_template_carries_hero_styles_with_hardcoded_values(app):
    from flask import render_template

    with app.app_context():
        survey = load_survey(REAL_SURVEY_PATH)
        html = render_template(
            'pdf/result.html', persona=survey['personas']['entrepreneur'],
            personas=survey['personas'], innovation=INNOVATION, audience=None,
        )
    assert 'persona-hero' in html
    assert '.persona-hero__head' in html
    assert '.persona-icon--card { width: 2.25rem' in re.sub(r'\s+', ' ', html)
    style = html[html.index('<style'):html.index('</style>')]
    assert 'var(--' not in style


# 8 ---------------------------------------------------------------------------

def test_pdf_generates_valid_bytes_for_the_hero_card(app):
    from app.pdf_utils import generate_result_pdf

    with app.app_context():
        survey = load_survey(REAL_SURVEY_PATH)
        pdf_bytes = generate_result_pdf(survey['personas']['entrepreneur'], survey['personas'])
    assert pdf_bytes.startswith(b'%PDF')


# 9 ---------------------------------------------------------------------------

def test_email_template_is_untouched_by_the_hero(app):
    from flask import render_template

    with app.app_context():
        survey = load_survey(REAL_SURVEY_PATH)
        html = render_template(
            'email/result.html', persona=survey['personas']['entrepreneur'],
            result_url='https://example.com/r', innovation=INNOVATION, audience=None,
        )
    assert 'persona-hero' not in html
