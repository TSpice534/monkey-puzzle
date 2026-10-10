"""Backlog #0051: the respondent's highlighted bar is outlined and the band
legend lays out in columns on phones."""
import os
import re

import pytest
from flask import render_template

from app.survey.charts import (
    HIGHLIGHT_BAR_STROKE, HIGHLIGHT_BAR_STROKE_WIDTH, render_innovation_curve_svg,
)
from app.survey.loader import clear_survey_cache, load_survey

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_SURVEY_PATH = os.path.join(REPO_ROOT, 'content', 'survey.yaml')
THEME_CSS_PATH = os.path.join(REPO_ROOT, 'app', 'static', 'css', 'theme.css')

INDIVIDUAL = 0


@pytest.fixture(autouse=True)
def _use_real_survey(app):
    app.config['SURVEY_PATH'] = REAL_SURVEY_PATH
    clear_survey_cache()
    yield
    clear_survey_cache()


def _real_bands():
    return load_survey(REAL_SURVEY_PATH)['innovation_curve']['bands']


def _css():
    with open(THEME_CSS_PATH, encoding='utf-8') as f:
        return re.sub(r'\s+', ' ', f.read())


def _rule_body(css, selector):
    match = re.search(re.escape(selector) + r' \{([^}]*)\}', css)
    assert match, selector
    return match.group(1)


def _legend_context(bands, current):
    return {
        'band': current['name'], 'score': current['min'], 'colour': current['colour'],
        'tagline': current['tagline'], 'description': current['description'],
        'curve_svg': render_innovation_curve_svg(current['min'], bands),
        'bands': [
            {'name': b['name'], 'colour': b['colour'], 'is_current': b['name'] == current['name']}
            for b in sorted(bands, key=lambda b: b['min'], reverse=True)
        ],
    }


def _complete_survey(client):
    token = client.get('/survey/start').headers['Location'].split('/survey/')[1].split('/step/')[0]
    client.post(f'/survey/{token}/step/1', data={'respondent_type': str(INDIVIDUAL)})
    client.post(f'/survey/{token}/step/2', data={'motivation': '4'})
    client.post(f'/survey/{token}/step/3', data={'ambition': '4'})
    client.post(f'/survey/{token}/step/4', data={'space_to_progress': '4'})
    client.post(f'/survey/{token}/step/5', data={'need_most': '0'})
    client.post(f'/survey/{token}/step/6', data={'have_enough': '0'})
    client.post(f'/survey/{token}/step/7', data={'profile_approach': '0', 'profile_scope': '0'})
    client.post(f'/survey/{token}/step/8', data={'topics': ['0', '1', '2']})
    client.post(f'/survey/{token}/step/9', data={'support_type': '0'})
    client.post(f'/survey/{token}/step/10', data={'target_groups': '0'})
    client.post(f'/survey/{token}/step/11', data={'why_reason': 'Because it matters.'})
    return token


# 1 ---------------------------------------------------------------------------

def test_highlighted_bar_has_class_and_stroke():
    svg = render_innovation_curve_svg(3, _real_bands())
    assert HIGHLIGHT_BAR_STROKE == '#212529'
    assert HIGHLIGHT_BAR_STROKE_WIDTH == 3
    assert svg.count('stroke=') == 1
    assert svg.count('curve-bar--current') == 1
    assert (f'class="curve-bar--current" stroke="{HIGHLIGHT_BAR_STROKE}" '
            f'stroke-width="{HIGHLIGHT_BAR_STROKE_WIDTH}"') in svg


# 2 ---------------------------------------------------------------------------

@pytest.mark.parametrize('band', _real_bands(), ids=lambda b: b['name'])
def test_every_real_band_highlight_carries_the_stroke(band):
    svg = render_innovation_curve_svg(band['min'], _real_bands())
    pattern = (rf'<rect[^>]*fill="{re.escape(band["colour"])}" fill-opacity="1"'
               rf'[^>]*stroke="#212529"')
    assert len(re.findall(pattern, svg)) == 1


# 3 ---------------------------------------------------------------------------

def test_no_score_means_no_stroke():
    svg = render_innovation_curve_svg(None, _real_bands())
    assert 'stroke=' not in svg
    assert 'curve-bar--current' not in svg


# 4 ---------------------------------------------------------------------------

def test_rect_count_unchanged():
    assert render_innovation_curve_svg(3, _real_bands()).count('<rect') == 16


# 5 ---------------------------------------------------------------------------

def test_out_of_range_score_outlines_end_bar():
    bands = _real_bands()
    top = max(bands, key=lambda b: b['max'])
    svg = render_innovation_curve_svg(999, bands)
    assert svg.count('stroke=') == 1
    assert re.search(rf'<rect[^>]*fill="{re.escape(top["colour"])}" fill-opacity="1"[^>]*stroke="#212529"', svg)


# 6 ---------------------------------------------------------------------------

def test_legend_ul_has_no_bootstrap_flex_utilities(app):
    bands = _real_bands()
    current = bands[0]
    with app.app_context():
        html = render_template('survey/_result_innovation.html', innovation=_legend_context(bands, current))
    ul_class = re.search(r'<ul class="([^"]*)"', html).group(1)
    assert ul_class.startswith('curve-legend')
    for banned in ('d-flex', 'flex-wrap', 'justify-content-center', 'gap-3'):
        assert banned not in ul_class


# 7 ---------------------------------------------------------------------------

def test_theme_css_rules():
    css = _css()
    assert '#' not in _rule_body(css, '.innovation-curve .curve-bar--current')
    assert 'var(--strong-text)' in _rule_body(css, '.innovation-curve .curve-bar--current')
    base = _rule_body(css, '.curve-legend')
    assert 'display: flex' in base and 'flex-wrap: wrap' in base
    mobile = css[css.index('@media (max-width: 767.98px)'):]
    mobile_legend = _rule_body(mobile, '.curve-legend')
    assert 'display: grid' in mobile_legend
    assert 'grid-template-columns' in mobile_legend
    assert css.count('@media (prefers-color-scheme: dark)') == 2
    assert css.count('@media (max-width: 767.98px)') == 1


# 8 ---------------------------------------------------------------------------

def test_pdf_template_legend_and_stroke(app):
    bands = _real_bands()
    current = next(b for b in bands if b['name'] == 'Innovators')
    persona = {
        'name': 'The Accountant', 'tagline': 't', 'description': 'd',
        'natural_allies': [], 'friends': [], 'necessity': [], 'case_studies': [], 'resources': [],
    }
    with app.app_context():
        html = render_template(
            'pdf/result.html', persona=persona, personas={'accountant': persona},
            innovation=_legend_context(bands, current), audience=None,
        )
    style = re.search(r'<style>(.*?)</style>', html, re.DOTALL).group(1)
    rule = re.search(r'\.curve-legend \{([^}]*)\}', style)
    assert rule and 'display: flex' in rule.group(1)
    assert 'var(--' not in style
    assert 'clamp(' not in style
    assert not re.search(r'\d\s*vw', style)
    assert '.card { display: block; }' in style
    assert 'stroke="#212529"' in html


# 9 ---------------------------------------------------------------------------

def test_real_result_page_has_one_outlined_bar(client):
    token = _complete_survey(client)
    body = client.get(f'/survey/{token}/result').get_data(as_text=True)
    svg = re.search(r'<svg[^>]*aria-label="Innovation curve[^>]*>.*?</svg>', body, re.DOTALL).group(0)
    assert svg.count('curve-bar--current') == 1
