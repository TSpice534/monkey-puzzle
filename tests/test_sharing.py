"""Phase 5 — share image, PDF download, email-a-copy, and the share-card
SVG renderer. Uses the small fixture survey (tests/fixtures/survey_min.yaml)
so driving a submission to completion is a handful of requests."""
import os

import pytest

from app import mail
from app.email_utils import _send_async
from app.models import Submission
from app.survey.charts import render_share_card_svg
from app.survey.loader import clear_survey_cache

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'survey_min.yaml')

PNG_MAGIC = b'\x89PNG\r\n\x1a\n'


@pytest.fixture(autouse=True)
def _use_fixture_survey(app):
    app.config['SURVEY_PATH'] = FIXTURE_PATH
    clear_survey_cache()
    yield
    clear_survey_cache()


def _start_new(client):
    response = client.get('/survey/start')
    return response.headers['Location'].split('/survey/')[1].split('/step/')[0]


def _complete_survey(client):
    """Drive the fixture survey to completion, landing on 'developer'."""
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'q_single': '0'})       # developer: 2
    client.post(f'/survey/{token}/step/2', data={'q_multi': []})
    client.post(f'/survey/{token}/step/3', data={'q_spectrum': '0'})
    client.post(f'/survey/{token}/step/4', data={'q_short_text': ''})
    return token


# ---------------------------------------------------------------------------
# result page — OG tags + share/PDF/email UI
# ---------------------------------------------------------------------------

def test_result_page_og_tags_and_share_links_use_the_real_result_url(client):
    """Regression test: `result_url`/`share_image_url` must be set at
    template scope (not inside {% block head %}) — Jinja block bodies don't
    share {% set %} variables with each other, so a variable set only
    inside one block silently renders empty everywhere else, including the
    LinkedIn share link and the email form built in {% block content %}."""
    token = _complete_survey(client)
    body = client.get(f'/survey/{token}/result').get_data(as_text=True)

    assert f'/survey/{token}/result' in body
    assert f'og:url" content="http://localhost/survey/{token}/result"' in body
    assert f'og:image" content="http://localhost/survey/{token}/share.png"' in body
    assert f'linkedin.com/sharing/share-offsite/?url=http' in body
    assert 'share-offsite/?url="' not in body  # the empty-URL regression


# ---------------------------------------------------------------------------
# share.png
# ---------------------------------------------------------------------------

def test_share_image_returns_png_for_completed_submission(client):
    token = _complete_survey(client)
    response = client.get(f'/survey/{token}/share.png')
    assert response.status_code == 200
    assert response.mimetype == 'image/png'
    assert response.data.startswith(PNG_MAGIC)


def test_share_image_has_long_lived_cache_header(client):
    token = _complete_survey(client)
    response = client.get(f'/survey/{token}/share.png')
    assert 'max-age' in response.headers['Cache-Control']


def test_share_image_404_before_completion(client):
    token = _start_new(client)
    response = client.get(f'/survey/{token}/share.png')
    assert response.status_code == 404


def test_share_image_404_unknown_token(client):
    response = client.get('/survey/not-a-real-token/share.png')
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# pdf
# ---------------------------------------------------------------------------

def test_download_pdf_returns_pdf_for_completed_submission(client):
    token = _complete_survey(client)
    response = client.get(f'/survey/{token}/pdf')
    assert response.status_code == 200
    assert response.mimetype == 'application/pdf'
    assert response.data.startswith(b'%PDF')


def test_download_pdf_content_disposition_names_the_persona(client):
    token = _complete_survey(client)
    response = client.get(f'/survey/{token}/pdf')
    disposition = response.headers['Content-Disposition']
    assert 'attachment' in disposition
    assert 'Developer' in disposition


def test_download_pdf_404_before_completion(client):
    token = _start_new(client)
    response = client.get(f'/survey/{token}/pdf')
    assert response.status_code == 404


def test_download_pdf_404_unknown_token(client):
    response = client.get('/survey/not-a-real-token/pdf')
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# email — route-level (validation, config gate, dispatch)
# ---------------------------------------------------------------------------

def test_email_result_without_mail_server_configured_flashes_warning(client, app):
    """TestConfig ships with no MAIL_SERVER — the route must not attempt to
    send, and must tell the user plainly rather than fail silently."""
    assert app.config.get('MAIL_SERVER') is None
    token = _complete_survey(client)

    response = client.post(f'/survey/{token}/email', data={'email': 'someone@example.com'},
                            follow_redirects=True)
    assert response.status_code == 200
    assert b"isn&#39;t configured" in response.data or b"isn't configured" in response.data


def test_email_result_with_invalid_email_does_not_dispatch(client, app, monkeypatch):
    app.config['MAIL_SERVER'] = 'smtp.example.com'
    sent = []
    monkeypatch.setattr(
        'app.survey.routes.send_result_email',
        lambda *a, **kw: sent.append((a, kw)),
    )
    token = _complete_survey(client)

    response = client.post(f'/survey/{token}/email', data={'email': 'not-an-email'},
                            follow_redirects=True)
    assert response.status_code == 200
    assert sent == []
    assert b'doesn' in response.data  # "doesn't look right"


def test_email_result_with_valid_email_dispatches_send_and_flashes_success(client, app, monkeypatch):
    app.config['MAIL_SERVER'] = 'smtp.example.com'
    sent = []
    monkeypatch.setattr(
        'app.survey.routes.send_result_email',
        lambda recipient, *a, **kw: sent.append(recipient),
    )
    token = _complete_survey(client)

    response = client.post(f'/survey/{token}/email', data={'email': 'Someone@Example.com'},
                            follow_redirects=True)
    assert response.status_code == 200
    # email_validator normalises the domain to lowercase (case-insensitive
    # per RFC), but leaves the local part as typed.
    assert sent == ['Someone@example.com']
    assert b'Sent!' in response.data


def test_email_result_404_before_completion(client, app):
    app.config['MAIL_SERVER'] = 'smtp.example.com'
    token = _start_new(client)
    response = client.post(f'/survey/{token}/email', data={'email': 'someone@example.com'})
    assert response.status_code == 404


def test_email_result_is_rate_limited(monkeypatch):
    """The one route that sends outbound mail on an anonymous request is
    rate-limited to guard against being used as a spam relay.

    RATELIMIT_ENABLED is read once by Flask-Limiter at init_app time, so
    this needs its own app instance built with it already True — mutating
    app.config after create_app() has no effect on an already-initialised
    limiter.
    """
    from app import create_app
    from app import db as _db
    from tests.conftest import TestConfig

    class RateLimitedConfig(TestConfig):
        RATELIMIT_ENABLED = True
        SURVEY_PATH = FIXTURE_PATH
        MAIL_SERVER = 'smtp.example.com'

    monkeypatch.setattr('app.survey.routes.send_result_email', lambda *a, **kw: None)

    application = create_app(RateLimitedConfig)
    with application.app_context():
        _db.create_all()
        client = application.test_client()
        token = _complete_survey(client)

        statuses = [
            client.post(f'/survey/{token}/email', data={'email': 'someone@example.com'}).status_code
            for _ in range(6)
        ]
        _db.session.remove()
        _db.drop_all()

    assert statuses[:5] == [302, 302, 302, 302, 302]
    assert statuses[5] == 429


# ---------------------------------------------------------------------------
# email — background send (real pipeline, no HTTP layer)
# ---------------------------------------------------------------------------

def test_send_async_attaches_generated_pdf(app):
    survey_personas = {
        'developer': {'name': 'The Developer', 'tagline': 'Builds things', 'description': 'x'},
    }
    persona = survey_personas['developer']
    msg_kwargs = dict(subject='subj', sender='sender@example.com', recipients=['user@example.com'])

    with mail.record_messages() as outbox:
        _send_async(app, msg_kwargs, persona, survey_personas, '<svg></svg>', 'https://example.com/r', None)

    assert len(outbox) == 1
    msg = outbox[0]
    assert msg.recipients == ['user@example.com']
    assert len(msg.attachments) == 1
    assert msg.attachments[0].filename == 'The_Developer_MonkeyPuzzle.pdf'
    assert msg.attachments[0].content_type == 'application/pdf'


def test_send_async_falls_back_without_attachment_if_pdf_generation_fails(app, monkeypatch):
    import app.email_utils as email_utils_module

    def _boom(*args, **kwargs):
        raise RuntimeError('WeasyPrint exploded')

    monkeypatch.setattr(email_utils_module, 'generate_result_pdf', _boom)

    survey_personas = {'developer': {'name': 'The Developer', 'tagline': 't', 'description': 'd'}}
    persona = survey_personas['developer']
    msg_kwargs = dict(subject='subj', sender='sender@example.com', recipients=['user@example.com'])

    with mail.record_messages() as outbox:
        _send_async(app, msg_kwargs, persona, survey_personas, '<svg></svg>', 'https://example.com/r', None)

    assert len(outbox) == 1
    assert outbox[0].attachments == []


# ---------------------------------------------------------------------------
# render_share_card_svg
# ---------------------------------------------------------------------------

def test_render_share_card_svg_contains_persona_name_and_tagline():
    persona = {'name': 'The Documenter', 'tagline': 'You make the invisible visible.'}
    personas = {'documenter': persona, 'developer': {'name': 'The Developer'}}
    scores = {'documenter': 5, 'developer': 1}

    svg = render_share_card_svg(persona, scores, personas)
    assert 'The Documenter' in svg
    assert 'You make the invisible visible.' in svg
    assert svg.startswith('<svg')


def test_render_share_card_svg_escapes_persona_fields():
    persona = {'name': '<script>alert(1)</script>', 'tagline': 'a & b'}
    personas = {'x': persona}
    svg = render_share_card_svg(persona, {'x': 1}, personas)
    assert '<script>' not in svg
    assert '&lt;script&gt;' in svg
    assert 'a &amp; b' in svg


def test_render_fingerprint_svg_rim_labels_stay_within_canvas_bounds():
    """Regression test: the longest persona name's rim label must not be
    positioned (or extend, accounting for text width) outside the SVG's own
    canvas — nested/rasterised <svg> clips silently at its viewBox edge."""
    from app.survey.charts import render_fingerprint_svg

    personas = {
        'entrepreneur': {'name': 'The Entrepreneur'},  # longest short name
        'documenter': {'name': 'The Documenter'},
        'developer': {'name': 'The Developer'},
    }
    scores = {pid: 1 for pid in personas}
    svg = render_fingerprint_svg(scores, personas, size=320)

    # Canvas is padded beyond `size` precisely so labels have margin;
    # assert the returned canvas really is larger than the logical size.
    import re
    width = float(re.search(r'width="([\d.]+)"', svg).group(1))
    assert width > 320
