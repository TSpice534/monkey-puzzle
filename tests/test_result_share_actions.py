"""Backlog #0050: result-page share actions, one primary and the rest secondary outline."""
import os
import re

import pytest

from app.survey.loader import clear_survey_cache, load_survey

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_SURVEY_PATH = os.path.join(REPO_ROOT, 'content', 'survey.yaml')
DESIGN_MD_PATH = os.path.join(REPO_ROOT, 'DESIGN.md')
THEME_CSS_PATH = os.path.join(REPO_ROOT, 'app', 'static', 'css', 'theme.css')

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


@pytest.fixture
def share(result_body):
    start = result_body.index('Share or save your result')
    end = result_body.rindex('<a ', start, result_body.index('Start again'))
    return result_body[start:end]


def _tag_containing(html, needle):
    pos = html.index(needle)
    open_at = max(html.rfind('<a ', 0, pos), html.rfind('<button ', 0, pos))
    return html[open_at:html.index('>', pos)]


# 1 ---------------------------------------------------------------------------

def test_linkedin_is_the_only_solid_primary(share):
    tag = _tag_containing(share, 'linkedin.com/sharing/share-offsite')
    assert 'btn-success' in tag
    assert 'btn-outline' not in tag
    assert share.count('btn btn-success') == 1


# 2 ---------------------------------------------------------------------------

def test_secondary_actions_are_brand_outline(share):
    pdf = share.index('Download PDF')
    cert = share.index('Download certificate')
    for tag in (share[share.rfind('<a ', 0, pdf):pdf],
                share[share.rfind('<a ', 0, cert):cert],
                _tag_containing(share, 'id="copy-caption"'),
                share[share.rfind('<button', 0, share.index('Email me a copy')):
                      share.index('Email me a copy')]):
        assert 'btn-outline-success' in tag


# 3 ---------------------------------------------------------------------------

def test_no_grey_buttons_in_share_section(share):
    assert 'btn-secondary' not in share
    assert 'btn-outline-secondary' not in share


# 4 ---------------------------------------------------------------------------

def test_share_section_preserves_ids_and_labels(share):
    for needle in ('id="copy-caption"', 'data-default-label="Copy caption"',
                   'data-copied-label="Copied!"', 'id="share-caption"',
                   'id="email"', 'name="email"', '/email', 'Share on LinkedIn',
                   'Download PDF', 'Download certificate', 'Email me a copy'):
        assert needle in share, needle
    assert re.search(r'id="copy-caption"\s+hidden', share)


# 5 ---------------------------------------------------------------------------

def test_theme_css_outline_success_uses_brand_tokens():
    css = _css()
    body = _rule_body(css, '.btn-outline-success')
    assert 'var(--brand-accent)' in body
    assert 'var(--brand-primary)' in body
    assert '#198754' not in body
    assert ':active' not in body
    assert css.index('.btn-outline-success {') < css.index('@media (max-width: 767.98px)')
    assert css.count('@media (prefers-color-scheme: dark)') == 2


# 6 ---------------------------------------------------------------------------

def test_design_md_share_actions_documented():
    with open(DESIGN_MD_PATH, encoding='utf-8') as f:
        text = f.read()
    assert 'share-actions:' in text
    assert any('brand-accent' in line and 'underlined' in line and 'ooter' in line
               for line in text.splitlines())
    assert 'Secondary actions look disabled' not in text
