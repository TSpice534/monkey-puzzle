"""Phase 5 — share image, PDF download, email-a-copy, and the share-card
SVG renderer. Uses the small fixture survey (tests/fixtures/survey_min.yaml)
so driving a submission to completion is a handful of requests."""
import os
import re

import pytest

from app import mail
from app.email_utils import _send_async
from app.models import Submission
from app.survey.charts import render_certificate_svg, render_share_card_svg
from app.survey.loader import clear_survey_cache
from app.survey.routes import _caption_context

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
    """Drive the fixture survey to completion, landing on 'inventor'."""
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'q_single': '0'})       # inventor: 2
    client.post(f'/survey/{token}/step/2', data={'q_multi': []})
    client.post(f'/survey/{token}/step/3', data={'q_spectrum': '0'})
    client.post(f'/survey/{token}/step/4', data={'q_short_text': ''})
    return token


def _complete_survey_as_accountant(client):
    """Same shape as `_complete_survey`, but picks the other q_single option
    so the submission lands on 'accountant' instead — a distinct persona,
    used to prove the asset cache doesn't collide across submissions."""
    token = _start_new(client)
    client.post(f'/survey/{token}/step/1', data={'q_single': '1'})       # accountant: 2
    client.post(f'/survey/{token}/step/2', data={'q_multi': []})
    client.post(f'/survey/{token}/step/3', data={'q_spectrum': '0'})
    client.post(f'/survey/{token}/step/4', data={'q_short_text': ''})
    return token


def _clear_asset_cache(app):
    """TestConfig's ASSET_CACHE_DIR is shared class-wide across the whole test
    run (content-addressed reuse is intended, not a leak — see conftest.py),
    so a cache-behaviour test must clear it first to guarantee a real miss on
    its own first request, regardless of what earlier tests already warmed."""
    cache_dir = app.config['ASSET_CACHE_DIR']
    for name in os.listdir(cache_dir):
        os.remove(os.path.join(cache_dir, name))


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


def test_share_image_is_cached_second_request_skips_rasterise(client, app, monkeypatch):
    """backlog #0022 — the on-disk asset cache should skip re-rasterising an
    already-rendered share card on a second request for the same token."""
    import cairosvg
    import app.survey.routes as routes_module

    _clear_asset_cache(app)

    calls = []
    real_svg2png = cairosvg.svg2png

    def _counting_svg2png(*args, **kwargs):
        calls.append(1)
        return real_svg2png(*args, **kwargs)

    monkeypatch.setattr(routes_module.cairosvg, 'svg2png', _counting_svg2png)

    token = _complete_survey(client)
    first = client.get(f'/survey/{token}/share.png')
    second = client.get(f'/survey/{token}/share.png')

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.mimetype == 'image/png'
    assert second.mimetype == 'image/png'
    assert first.data == second.data
    assert len(calls) == 1


def test_share_image_cache_key_does_not_collide_across_different_personas(client, app):
    """backlog #0022 — the cache is keyed by the rendered SVG (persona-
    specific), not by token, so two submissions landing on different
    personas must get their own distinct cache entry and their own
    correct image, never share or clobber one another's."""
    _clear_asset_cache(app)

    inventor_token = _complete_survey(client)
    accountant_token = _complete_survey_as_accountant(client)

    inventor_png = client.get(f'/survey/{inventor_token}/share.png').data
    accountant_png = client.get(f'/survey/{accountant_token}/share.png').data

    assert inventor_png.startswith(PNG_MAGIC)
    assert accountant_png.startswith(PNG_MAGIC)
    assert inventor_png != accountant_png

    # Re-fetching each must still return its own image, not the other's.
    assert client.get(f'/survey/{inventor_token}/share.png').data == inventor_png
    assert client.get(f'/survey/{accountant_token}/share.png').data == accountant_png

    cache_files = [f for f in os.listdir(app.config['ASSET_CACHE_DIR']) if f.endswith('.png')]
    assert len(cache_files) == 2


# ---------------------------------------------------------------------------
# certificate.png (backlog #0030)
# ---------------------------------------------------------------------------

def test_certificate_returns_png_for_completed_submission(client):
    token = _complete_survey(client)
    response = client.get(f'/survey/{token}/certificate.png')
    assert response.status_code == 200
    assert response.mimetype == 'image/png'
    assert response.data.startswith(PNG_MAGIC)


def test_certificate_content_disposition_names_the_persona(client):
    token = _complete_survey(client)
    response = client.get(f'/survey/{token}/certificate.png')
    disposition = response.headers['Content-Disposition']
    assert 'attachment' in disposition
    assert 'Inventor' in disposition
    assert '.png' in disposition


def test_certificate_has_long_lived_cache_header(client):
    token = _complete_survey(client)
    response = client.get(f'/survey/{token}/certificate.png')
    assert 'max-age' in response.headers['Cache-Control']


def test_certificate_404_before_completion(client):
    token = _start_new(client)
    response = client.get(f'/survey/{token}/certificate.png')
    assert response.status_code == 404


def test_certificate_404_unknown_token(client):
    response = client.get('/survey/not-a-real-token/certificate.png')
    assert response.status_code == 404


def test_certificate_is_cached_second_request_skips_rasterise(client, app, monkeypatch):
    """backlog #0022 — the on-disk asset cache should skip re-rasterising an
    already-rendered certificate on a second request for the same token."""
    import cairosvg
    import app.survey.routes as routes_module

    _clear_asset_cache(app)

    calls = []
    real_svg2png = cairosvg.svg2png

    def _counting_svg2png(*args, **kwargs):
        calls.append(1)
        return real_svg2png(*args, **kwargs)

    monkeypatch.setattr(routes_module.cairosvg, 'svg2png', _counting_svg2png)

    token = _complete_survey(client)
    first = client.get(f'/survey/{token}/certificate.png')
    second = client.get(f'/survey/{token}/certificate.png')

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.mimetype == 'image/png'
    assert second.mimetype == 'image/png'
    assert first.data == second.data
    assert len(calls) == 1


def test_certificate_and_share_image_are_distinct_cache_entries(client, app):
    """backlog #0030 — the certificate and share-card PNGs are different
    renders of the same submission, so they must not collide in the
    content-addressed asset cache."""
    _clear_asset_cache(app)

    token = _complete_survey(client)
    share_png = client.get(f'/survey/{token}/share.png').data
    certificate_png = client.get(f'/survey/{token}/certificate.png').data

    assert share_png != certificate_png

    cache_files = [f for f in os.listdir(app.config['ASSET_CACHE_DIR']) if f.endswith('.png')]
    assert len(cache_files) == 2


def test_result_page_offers_a_certificate_download_link(client):
    token = _complete_survey(client)
    body = client.get(f'/survey/{token}/result').get_data(as_text=True)
    assert '/certificate.png' in body


def test_result_page_omits_the_caption_block_when_survey_has_no_share_caption(client):
    """The fixture survey (survey_min.yaml) has no `share_caption` config, so
    `_caption_context` returns None and the caption block must not render."""
    token = _complete_survey(client)
    body = client.get(f'/survey/{token}/result').get_data(as_text=True)
    assert 'id="share-caption"' not in body


# ---------------------------------------------------------------------------
# _caption_context (backlog #0030) — direct calls, defensive .format() path
# ---------------------------------------------------------------------------

_CAPTION_PERSONA = {'name': 'The Inventor'}


def test_caption_context_returns_none_on_unknown_placeholder():
    survey = {'share_caption': {'template': 'Hi {foo}, take the survey! {url}'}}
    assert _caption_context(_CAPTION_PERSONA, survey, 'https://example.com/') is None


def test_caption_context_returns_none_on_bare_braces_placeholder():
    survey = {'share_caption': {'template': 'Hi {}, take the survey! {url}'}}
    assert _caption_context(_CAPTION_PERSONA, survey, 'https://example.com/') is None


def test_caption_context_returns_none_on_unbalanced_brace():
    survey = {'share_caption': {'template': 'Hi {persona, take the survey! {url}'}}
    assert _caption_context(_CAPTION_PERSONA, survey, 'https://example.com/') is None


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
    assert 'Inventor' in disposition


def test_download_pdf_404_before_completion(client):
    token = _start_new(client)
    response = client.get(f'/survey/{token}/pdf')
    assert response.status_code == 404


def test_download_pdf_404_unknown_token(client):
    response = client.get('/survey/not-a-real-token/pdf')
    assert response.status_code == 404


def test_download_pdf_is_cached_second_request_skips_weasyprint(client, app, monkeypatch):
    """backlog #0022 — the on-disk asset cache should skip re-running
    WeasyPrint on a second request for the same token."""
    import app.survey.routes as routes_module

    _clear_asset_cache(app)

    calls = []
    real_html_to_pdf = routes_module.html_to_pdf

    def _counting_html_to_pdf(*args, **kwargs):
        calls.append(1)
        return real_html_to_pdf(*args, **kwargs)

    monkeypatch.setattr(routes_module, 'html_to_pdf', _counting_html_to_pdf)

    token = _complete_survey(client)
    first = client.get(f'/survey/{token}/pdf')
    second = client.get(f'/survey/{token}/pdf')

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.data.startswith(b'%PDF')
    assert second.data.startswith(b'%PDF')
    assert first.data == second.data
    assert len(calls) == 1


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
        _send_async(app, msg_kwargs, persona, survey_personas, 'https://example.com/r', None)

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
        _send_async(app, msg_kwargs, persona, survey_personas, 'https://example.com/r', None)

    assert len(outbox) == 1
    assert outbox[0].attachments == []


# ---------------------------------------------------------------------------
# render_share_card_svg
# ---------------------------------------------------------------------------

def test_render_share_card_svg_contains_persona_name_and_tagline():
    persona = {'name': 'The Accountant', 'tagline': 'You make the numbers tell the truth.'}

    svg = render_share_card_svg(persona)
    assert 'The Accountant' in svg
    assert 'You make the numbers tell the truth.' in svg
    assert svg.startswith('<svg')


def test_render_share_card_svg_escapes_persona_fields():
    persona = {'name': '<script>alert(1)</script>', 'tagline': 'a & b'}
    svg = render_share_card_svg(persona)
    assert '<script>' not in svg
    assert '&lt;script&gt;' in svg
    assert 'a &amp; b' in svg


# ---------------------------------------------------------------------------
# render_certificate_svg (backlog #0030)
# ---------------------------------------------------------------------------

def test_render_certificate_svg_contains_persona_name_and_tagline():
    persona = {'name': 'The Accountant', 'tagline': 'You make the numbers tell the truth.'}

    svg = render_certificate_svg(persona)
    assert 'The Accountant' in svg
    assert 'You make the numbers tell the truth.' in svg
    assert svg.startswith('<svg')


def test_render_certificate_svg_escapes_persona_fields():
    persona = {'name': '<script>alert(1)</script>', 'tagline': 'a & b'}
    svg = render_certificate_svg(persona)
    assert '<script>' not in svg
    assert '&lt;script&gt;' in svg
    assert 'a &amp; b' in svg


def test_render_certificate_svg_names_the_band_as_text_when_given():
    # '#2e7d32' is also the hardcoded fallback accent colour in charts.py,
    # so asserting on it here would pass even if `band_colour` were ignored
    # entirely — use a colour that only appears if the parameter is honoured.
    persona = {'name': 'The Inventor', 'tagline': 'Tagline'}
    svg = render_certificate_svg(persona, band='Innovators', band_colour='#123456')
    assert 'Innovators' in svg
    assert 'fill="#123456"' in svg


def test_render_certificate_svg_without_a_band_does_not_raise_and_omits_the_band_line():
    persona = {'name': 'The Inventor', 'tagline': 'Tagline'}
    svg = render_certificate_svg(persona, band=None)
    assert svg.startswith('<svg')
    assert 'Innovation curve' not in svg


def test_render_certificate_svg_band_given_without_band_colour_falls_back_to_default_accent():
    """spec edge case: `band` truthy but `band_colour` falsy must not raise,
    and the swatch/frame fall back to the default accent (#2e7d32)."""
    persona = {'name': 'The Inventor', 'tagline': 'Tagline'}
    svg = render_certificate_svg(persona, band='Innovators', band_colour=None)
    assert svg.startswith('<svg')
    assert 'Innovators' in svg
    assert 'fill="#2e7d32"' in svg


def test_render_certificate_svg_band_colour_given_without_band_omits_band_line():
    """spec edge case: `band_colour` truthy but `band` falsy must not raise,
    and the band line must be omitted entirely (never conveyed by colour alone)."""
    persona = {'name': 'The Inventor', 'tagline': 'Tagline'}
    svg = render_certificate_svg(persona, band=None, band_colour='#123456')
    assert svg.startswith('<svg')
    assert 'Innovation curve' not in svg


# ---------------------------------------------------------------------------
# render_innovation_curve_svg (backlog #0011)
# ---------------------------------------------------------------------------

_CURVE_BANDS = [
    {'name': 'Laggards', 'min': 0, 'max': 2, 'colour': '#c0392b'},
    {'name': 'Late Majority', 'min': 3, 'max': 7, 'colour': '#e67e22'},
    {'name': 'Early Majority', 'min': 8, 'max': 12, 'colour': '#f1c40f'},
    {'name': 'Early Adopters', 'min': 13, 'max': 14, 'colour': '#7cb342'},
    {'name': 'Innovators', 'min': 15, 'max': 20, 'colour': '#2e7d32'},
]


def test_render_innovation_curve_svg_returns_svg_with_role_and_aria_label():
    from app.survey.charts import render_innovation_curve_svg

    svg = render_innovation_curve_svg(14, _CURVE_BANDS)
    assert svg.startswith('<svg')
    assert 'role="img"' in svg
    assert 'aria-label="' in svg
    assert '14' in svg  # the score is named in the aria-label


def test_render_innovation_curve_svg_draws_one_bar_per_score_point():
    from app.survey.charts import render_innovation_curve_svg

    svg = render_innovation_curve_svg(10, _CURVE_BANDS)
    assert svg.count('<rect') == 21  # 0..20 inclusive


def test_render_innovation_curve_svg_highlights_exactly_one_bar_at_full_opacity():
    from app.survey.charts import UNHIGHLIGHTED_BAR_OPACITY, render_innovation_curve_svg

    svg = render_innovation_curve_svg(14, _CURVE_BANDS)
    band_colour = next(b['colour'] for b in _CURVE_BANDS if b['min'] <= 14 <= b['max'])

    # All 21 bars keep their own band's bold colour — only opacity changes.
    assert svg.count(f'fill="{band_colour}"') == 2  # both points in the 13-14 band

    assert svg.count('fill-opacity="1"') == 1
    assert svg.count(f'fill-opacity="{UNHIGHLIGHTED_BAR_OPACITY}"') == 20


def test_render_innovation_curve_svg_with_no_score_has_no_highlight_and_does_not_raise():
    from app.survey.charts import UNHIGHLIGHTED_BAR_OPACITY, render_innovation_curve_svg

    svg = render_innovation_curve_svg(None, _CURVE_BANDS)
    assert svg.startswith('<svg')
    assert 'fill-opacity="1"' not in svg
    assert svg.count(f'fill-opacity="{UNHIGHLIGHTED_BAR_OPACITY}"') == 21


def test_render_innovation_curve_svg_empty_bands_returns_empty_string():
    from app.survey.charts import render_innovation_curve_svg

    assert render_innovation_curve_svg(10, []) == ''


def test_render_innovation_curve_svg_includes_all_five_band_names_as_labels():
    from app.survey.charts import render_innovation_curve_svg

    svg = render_innovation_curve_svg(5, _CURVE_BANDS)
    for band in _CURVE_BANDS:
        assert f'>{band["name"]}<' in svg


# ---------------------------------------------------------------------------
# render_innovation_curve_svg label-collision layout (backlog #0029) — the
# real survey's bands, where the Innovators band is a single bar wide.
# ---------------------------------------------------------------------------

_CURVE_BANDS_REAL = [
    {'name': 'Laggards', 'min': 0, 'max': 2, 'colour': '#c0392b'},
    {'name': 'Late Majority', 'min': 3, 'max': 7, 'colour': '#e67e22'},
    {'name': 'Early Majority', 'min': 8, 'max': 12, 'colour': '#f1c40f'},
    {'name': 'Early Adopters', 'min': 13, 'max': 14, 'colour': '#7cb342'},
    {'name': 'Innovators', 'min': 15, 'max': 15, 'colour': '#2e7d32'},
]

_LABEL_RE = re.compile(r'<text x="([\d.]+)"[^>]*font-size="([\d.]+)"[^>]*>([^<]+)</text>')


def _label_boxes(svg):
    from app.survey.charts import _estimate_text_width

    boxes = []
    for x_str, font_size_str, name in _LABEL_RE.findall(svg):
        x = float(x_str)
        font_size = float(font_size_str)
        half_width = _estimate_text_width(name, font_size) / 2
        boxes.append((x - half_width, x + half_width))
    boxes.sort(key=lambda box: box[0])
    return boxes


def _assert_label_boxes_do_not_overlap(boxes, width):
    for left, right in boxes:
        assert left >= 0
        assert right <= width
    for previous, current in zip(boxes, boxes[1:]):
        assert current[0] >= previous[1]


def test_render_innovation_curve_svg_band_labels_do_not_overlap():
    from app.survey.charts import render_innovation_curve_svg

    svg = render_innovation_curve_svg(15, _CURVE_BANDS_REAL)
    boxes = _label_boxes(svg)
    assert len(boxes) == 5
    _assert_label_boxes_do_not_overlap(boxes, 640)


def test_render_innovation_curve_svg_keeps_every_band_name_verbatim_when_a_band_is_one_bar_wide():
    from app.survey.charts import render_innovation_curve_svg

    svg = render_innovation_curve_svg(15, _CURVE_BANDS_REAL)
    for band in _CURVE_BANDS_REAL:
        assert f'>{band["name"]}<' in svg


def test_render_innovation_curve_svg_band_labels_do_not_overlap_at_narrow_width():
    from app.survey.charts import render_innovation_curve_svg

    svg = render_innovation_curve_svg(15, _CURVE_BANDS_REAL, width=320)
    boxes = _label_boxes(svg)
    assert len(boxes) == 5
    _assert_label_boxes_do_not_overlap(boxes, 320)
