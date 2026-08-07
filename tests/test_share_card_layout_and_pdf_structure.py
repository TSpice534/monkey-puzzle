"""Independent verification of backlog #0025 (remove the radar/fingerprint
chart from the PDF download, emailed PDF copy, and share-card PNG) —
complementing (not duplicating) the coder's own updated tests in
test_sharing.py.

Focus areas independently verified here:
  1. `render_share_card_svg(persona)`'s new single-arg signature produces
     markup matching the spec's exact y/font-size/fill layout table.
  2. The redesigned layout doesn't visually overflow the fixed 1200x630
     canvas for the longest real persona name ("The Entrepreneur") and for
     a long, natural-language tagline near the ~60-char budget the spec's
     sizing rationale assumed — verified by actually rasterising the SVG
     (via cairosvg, the same library the real `share_image` route uses) and
     measuring the true unclipped ink extent, not just eyeballing the
     f-string.
  3. Failure case: the old three-arg `render_share_card_svg(persona, scores,
     personas)` call shape is rejected (TypeError) now that `scores`/
     `personas` are gone — confirms the signature change is a real, hard
     contract change, not just cosmetic.
  4. No leftover references to the deleted `render_fingerprint_svg` (or its
     orphaned `_RING_FRACTIONS`/`_LABEL_PAD_FRACTION`/`_CANVAS_FACTOR`
     constants) anywhere in `app/` or `tests/`, except the one docstring
     mention inside `render_innovation_curve_svg` the spec explicitly said
     to leave untouched.
  5. `pdf/result.html` renders without the `.chart-col`/`.results-row`
     markup and without any `fingerprint_svg` reference, with the persona
     card and innovation-curve card both still intact.
  6. Failure case: the emailed PDF copy ("...with the fingerprint chart,
     are attached as a PDF") is now stale/false — the attached PDF no
     longer has a fingerprint chart, in either surface (web result page,
     per #0020) — since this backlog's own goal is "remove it everywhere".
"""
import io
import os
import re

import cairosvg
import pytest
from PIL import Image, ImageChops

from app.survey.charts import SHARE_CARD_HEIGHT, SHARE_CARD_WIDTH, render_share_card_svg
from app.survey.loader import load_survey

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_SURVEY_PATH = os.path.join(REPO_ROOT, 'content', 'survey.yaml')
APP_DIR = os.path.join(REPO_ROOT, 'app')
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

# The one spot the spec explicitly said to leave alone.
ALLOWED_FINGERPRINT_SVG_REFERENCE = (
    os.path.join(APP_DIR, 'survey', 'charts.py'),
    "Styled on `render_fingerprint_svg`:",
)


def _iter_py_and_html_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ('__pycache__', '.venv')]
        for filename in filenames:
            if filename.endswith(('.py', '.html')):
                yield os.path.join(dirpath, filename)


def _text_element_attrs(svg: str):
    """Parse every <text ...>content</text> element into
    {content: {attr: value}}, tolerant of attribute ordering."""
    out = {}
    for attrs_blob, content in re.findall(r'<text([^>]*)>([^<]*)</text>', svg):
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', attrs_blob))
        out[content] = attrs
    return out


def _rasterize_unclipped(svg: str, expand_factor: int = 3) -> Image.Image:
    """Rasterise `svg` on a canvas widened well past SHARE_CARD_WIDTH (same
    coordinate system, same font sizes/positions) so any text that would be
    clipped at the real 1200px edge is still fully painted — letting us
    measure its true horizontal extent instead of just trusting it fits."""
    widened_w = SHARE_CARD_WIDTH * expand_factor
    widened = svg.replace(
        f'width="{SHARE_CARD_WIDTH}" height="{SHARE_CARD_HEIGHT}" '
        f'viewBox="0 0 {SHARE_CARD_WIDTH} {SHARE_CARD_HEIGHT}"',
        f'width="{widened_w}" height="{SHARE_CARD_HEIGHT}" '
        f'viewBox="0 0 {widened_w} {SHARE_CARD_HEIGHT}"',
    ).replace(
        f'<rect width="{SHARE_CARD_WIDTH}" height="{SHARE_CARD_HEIGHT}" fill="#f8f9fa" />',
        f'<rect width="{widened_w}" height="{SHARE_CARD_HEIGHT}" fill="#f8f9fa" />',
    )
    assert widened != svg, 'widening substitution did not match — SVG markup shape changed'

    png_bytes = cairosvg.svg2png(bytestring=widened.encode(), output_width=widened_w,
                                  output_height=SHARE_CARD_HEIGHT)
    return Image.open(io.BytesIO(png_bytes)).convert('RGB')


def _ink_bbox(img: Image.Image, background=(248, 249, 250)):
    """Bounding box (left, upper, right, lower) of every pixel that differs
    from the card's flat background colour — i.e. the accent bar plus every
    text glyph actually painted, clipped or not."""
    bg = Image.new('RGB', img.size, background)
    return ImageChops.difference(img, bg).getbbox()


# ---------------------------------------------------------------------------
# 1. New single-arg signature — markup matches the spec's layout table
# ---------------------------------------------------------------------------

def test_render_share_card_svg_new_signature_matches_spec_layout_table():
    persona = {'name': 'The Communicator', 'tagline': 'You are the voice!'}

    svg = render_share_card_svg(persona)

    assert svg.startswith(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SHARE_CARD_WIDTH}" '
        f'height="{SHARE_CARD_HEIGHT}" viewBox="0 0 {SHARE_CARD_WIDTH} {SHARE_CARD_HEIGHT}"'
    )
    assert 'role="img"' in svg
    assert 'aria-label="The Communicator — The Monkey Puzzle"' in svg

    elements = _text_element_attrs(svg)

    eyebrow = elements['THE MONKEY PUZZLE']
    assert eyebrow['x'] == '70' and eyebrow['y'] == '100'
    assert eyebrow['font-size'] == '26' and eyebrow['fill'] == '#6c757d'
    assert eyebrow['letter-spacing'] == '2'

    lead_in = elements['Your sustainable who:']
    assert lead_in['x'] == '70' and lead_in['y'] == '285'
    assert lead_in['font-size'] == '36' and lead_in['fill'] == '#6c757d'

    name = elements['The Communicator']
    assert name['x'] == '70' and name['y'] == '390'
    assert name['font-size'] == '84' and name['font-weight'] == '700'
    assert name['fill'] == '#212529'

    tagline = elements['You are the voice!']
    assert tagline['x'] == '70' and tagline['y'] == '470'
    assert tagline['font-size'] == '34' and tagline['fill'] == '#495057'

    # The radar block is gone — no nested <g transform=...> wrapper left over.
    assert '<g transform' not in svg


# ---------------------------------------------------------------------------
# 2. No visible overflow of the fixed 1200x630 canvas
# ---------------------------------------------------------------------------

def test_render_share_card_svg_longest_real_persona_name_stays_within_canvas(app):
    """'The Entrepreneur' is the longest name in the real persona set — the
    changes doc calls this out by name as the layout's worst case."""
    with app.app_context():
        survey = load_survey(REAL_SURVEY_PATH)
    persona = survey['personas']['entrepreneur']
    assert persona['name'] == 'The Entrepreneur'

    svg = render_share_card_svg(persona)
    img = _rasterize_unclipped(svg)
    bbox = _ink_bbox(img)

    assert bbox is not None
    left, upper, right, lower = bbox
    assert right < SHARE_CARD_WIDTH, (
        f'ink extends to x={right}, past the {SHARE_CARD_WIDTH}px canvas — '
        f'"{persona["name"]}" overflows the share card'
    )
    assert lower <= SHARE_CARD_HEIGHT


def test_render_share_card_svg_long_tagline_stays_within_canvas():
    """~60 chars of natural-language tagline — the width budget the spec's
    sizing rationale explicitly reasons about."""
    long_tagline = 'You make the numbers tell the truth and nobody else wants to.'
    assert len(long_tagline) >= 60
    persona = {'name': 'The Entrepreneur', 'tagline': long_tagline}

    svg = render_share_card_svg(persona)
    img = _rasterize_unclipped(svg)
    bbox = _ink_bbox(img)

    assert bbox is not None
    right = bbox[2]
    assert right < SHARE_CARD_WIDTH, (
        f'ink extends to x={right}, past the {SHARE_CARD_WIDTH}px canvas for '
        f'a {len(long_tagline)}-char tagline'
    )


def test_render_share_card_svg_short_content_stays_comfortably_within_canvas(app):
    """Happy path sanity check against a real, short persona."""
    with app.app_context():
        survey = load_survey(REAL_SURVEY_PATH)
    persona = survey['personas']['accountant']

    svg = render_share_card_svg(persona)
    img = _rasterize_unclipped(svg)
    bbox = _ink_bbox(img)

    assert bbox is not None
    assert bbox[2] < SHARE_CARD_WIDTH


# ---------------------------------------------------------------------------
# 3. Failure case: the old three-arg call shape is gone for good
# ---------------------------------------------------------------------------

def test_render_share_card_svg_rejects_the_old_three_arg_call_shape():
    persona = {'name': 'The Inventor', 'tagline': 'You are the thinker!'}
    with pytest.raises(TypeError):
        render_share_card_svg(persona, {'sustainability': 5}, {'inventor': persona})


# ---------------------------------------------------------------------------
# 4. No leftover references to the deleted generator/constants
# ---------------------------------------------------------------------------

def test_no_leftover_references_to_deleted_fingerprint_helpers():
    banned_symbols = ('render_fingerprint_svg', '_RING_FRACTIONS', '_LABEL_PAD_FRACTION',
                       '_CANVAS_FACTOR')
    this_file = os.path.abspath(__file__)
    hits = []
    for path in list(_iter_py_and_html_files(APP_DIR)) + list(_iter_py_and_html_files(TESTS_DIR)):
        if path == this_file:
            continue  # this test file names the banned symbols on purpose, to describe them
        with open(path, encoding='utf-8') as f:
            for lineno, line in enumerate(f, start=1):
                for symbol in banned_symbols:
                    if symbol in line:
                        hits.append((path, lineno, symbol, line.strip()))

    unexpected = [
        hit for hit in hits
        if not (hit[0] == ALLOWED_FINGERPRINT_SVG_REFERENCE[0]
                and ALLOWED_FINGERPRINT_SVG_REFERENCE[1] in hit[3])
    ]
    assert unexpected == [], f'unexpected leftover references: {unexpected}'


# ---------------------------------------------------------------------------
# 5. pdf/result.html — chart column actually gone, persona card intact
# ---------------------------------------------------------------------------

def test_pdf_template_renders_without_chart_column_or_fingerprint_reference(app):
    from flask import render_template

    with app.app_context():
        survey = load_survey(REAL_SURVEY_PATH)
    persona = survey['personas']['entrepreneur']
    innovation = {
        'band': 'Innovators', 'score': 18, 'colour': '#2e7d32',
        'tagline': 'You are an Innovator', 'description': 'x',
    }

    with app.app_context():
        html = render_template(
            'pdf/result.html', persona=persona, personas=survey['personas'],
            innovation=innovation, audience=None,
        )

    assert 'chart-col' not in html
    assert 'results-row' not in html
    assert 'fingerprint_svg' not in html
    assert 'fingerprint' not in html.lower()

    # Persona card still renders, full width.
    assert 'The Entrepreneur' in html
    assert persona['tagline'] in html
    # Innovation-curve card (untouched per spec) still renders alongside it.
    assert 'Innovators' in html


def test_pdf_generates_real_bytes_without_the_chart_column(app):
    """End-to-end WeasyPrint smoke test against the real survey content —
    confirms the freed-up `.chart-col` removal didn't break the page layout
    enough to blow up rendering."""
    from app.pdf_utils import generate_result_pdf

    with app.app_context():
        survey = load_survey(REAL_SURVEY_PATH)
        persona = survey['personas']['entrepreneur']
        pdf_bytes = generate_result_pdf(persona, survey['personas'])

    assert pdf_bytes.startswith(b'%PDF')
    assert len(pdf_bytes) > 1000


# ---------------------------------------------------------------------------
# 6. Failure case: emailed-PDF copy still promises a chart that's gone
# ---------------------------------------------------------------------------

def test_email_bodies_do_not_promise_a_fingerprint_chart_in_the_attached_pdf(app):
    """Backlog #0025's whole point is removing the chart from the emailed
    PDF copy. Both email bodies still say '...with the fingerprint chart,
    are attached as a PDF' — that's now false: the attached PDF has no
    chart at all. This is stale copy left over from before #0020/#0025,
    not something the spec's file list touched, but it directly
    contradicts this backlog's own goal."""
    from flask import render_template

    with app.app_context():
        survey = load_survey(REAL_SURVEY_PATH)
    persona = survey['personas']['entrepreneur']

    with app.app_context():
        text_body = render_template(
            'email/result.txt', persona=persona, result_url='https://example.com/r',
            innovation=None, audience=None,
        )
        html_body = render_template(
            'email/result.html', persona=persona, result_url='https://example.com/r',
            innovation=None, audience=None,
        )

    assert 'fingerprint' not in text_body.lower(), (
        'email/result.txt still promises a fingerprint chart in the attached PDF'
    )
    assert 'fingerprint' not in html_body.lower(), (
        'email/result.html still promises a fingerprint chart in the attached PDF'
    )
