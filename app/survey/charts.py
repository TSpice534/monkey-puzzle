"""Inline-SVG radar ("fingerprint") chart over the nine personas.

Adapts the trig/inline-SVG style of Donut Toolkit's
`pdf_utils.py::_generate_donut_svg` — hand-built SVG, no JS, no external
assets, so it renders unaffected by the CSP. Designed as a reusable pure
function so a later phase (share image / PDF) can call it too.
"""
import math
from xml.sax.saxutils import escape

# Concentric guide rings, as fractions of the outer radius.
_RING_FRACTIONS = (0.25, 0.5, 0.75, 1.0)

# Label-margin padding added around `size` by render_fingerprint_svg (see
# there for why); callers that need the actual rendered canvas footprint
# for a given `size` should use `size * _CANVAS_FACTOR`.
_LABEL_PAD_FRACTION = 0.22
_CANVAS_FACTOR = 1 + 2 * _LABEL_PAD_FRACTION


def render_fingerprint_svg(scores: dict, personas: dict, size: int = 320) -> str:
    """Return an inline <svg> string: a radar/spider chart with one axis per
    persona (nine axes), the point on each axis proportional to that
    persona's score in `scores`.

    Normalises each axis against the max value in `scores` (so the winner
    reaches the outer ring); if all scores are zero or negative, every
    point is drawn at the centre without dividing by zero.
    """
    persona_ids = list(personas.keys())
    n = len(persona_ids)
    if n == 0:
        return ''

    # The canvas is padded beyond `size` so long rim labels (e.g.
    # "Entrepreneur") never clip against the SVG's own viewport edge —
    # nested/rasterised <svg> clips at its viewBox bounds regardless of
    # the geometry inside it, unlike overflow-visible root-level SVG.
    pad = size * _LABEL_PAD_FRACTION
    canvas = size + 2 * pad
    cx = cy = canvas / 2
    outer_radius = size * 0.36           # leave room for the rim labels
    start_angle = -math.pi / 2           # first axis points straight up
    step = (2 * math.pi) / n

    def point(radius, i):
        angle = start_angle + i * step
        return cx + radius * math.cos(angle), cy + radius * math.sin(angle)

    # Only positive contributions move a point off-centre; an all-zero
    # (or all-negative) vector renders every point at the centre.
    positive_scores = [max(scores.get(pid, 0.0), 0) for pid in persona_ids]
    max_score = max(positive_scores) if positive_scores else 0

    # ------------------------------------------------------------------
    # Guide rings (concentric polygons) + axis spokes
    # ------------------------------------------------------------------
    rings_svg = []
    for fraction in _RING_FRACTIONS:
        ring_points = [point(outer_radius * fraction, i) for i in range(n)]
        path = ' '.join(f'{x:.2f},{y:.2f}' for x, y in ring_points)
        rings_svg.append(
            f'<polygon points="{path}" fill="none" stroke="#dee2e6" stroke-width="1" />'
        )

    spokes_svg = []
    for i in range(n):
        x, y = point(outer_radius, i)
        spokes_svg.append(
            f'<line x1="{cx:.2f}" y1="{cy:.2f}" x2="{x:.2f}" y2="{y:.2f}" '
            f'stroke="#dee2e6" stroke-width="1" />'
        )

    # ------------------------------------------------------------------
    # Score polygon
    # ------------------------------------------------------------------
    score_points = [
        point(outer_radius * ((raw / max_score) if max_score > 0 else 0), i)
        for i, raw in enumerate(positive_scores)
    ]
    score_path = ' '.join(f'{x:.2f},{y:.2f}' for x, y in score_points)
    score_svg = (
        f'<polygon points="{score_path}" fill="#2e7d32" fill-opacity="0.35" '
        f'stroke="#2e7d32" stroke-width="2" />'
    )

    # ------------------------------------------------------------------
    # Rim labels (short persona names)
    # ------------------------------------------------------------------
    label_font_size = size * 0.032
    labels_svg = []
    for i, pid in enumerate(persona_ids):
        x, y = point(outer_radius * 1.16, i)
        name = personas[pid].get('name', pid)
        short_name = escape(name.replace('The ', ''))
        angle = start_angle + i * step
        cos_a = math.cos(angle)
        if cos_a > 0.3:
            anchor = 'start'
        elif cos_a < -0.3:
            anchor = 'end'
        else:
            anchor = 'middle'
        labels_svg.append(
            f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}" '
            f'dominant-baseline="middle" font-family="Arial,sans-serif" '
            f'font-size="{label_font_size:.1f}" fill="#212529">{short_name}</text>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas:.1f}" height="{canvas:.1f}" '
        f'viewBox="0 0 {canvas:.1f} {canvas:.1f}" role="img" aria-label="Persona fingerprint radar chart">'
        + ''.join(rings_svg)
        + ''.join(spokes_svg)
        + score_svg
        + ''.join(labels_svg)
        + '</svg>'
    )


# Standard OpenGraph image size (1200x630) so LinkedIn/Twitter/Facebook
# crawlers render a full, uncropped preview.
SHARE_CARD_WIDTH = 1200
SHARE_CARD_HEIGHT = 630


def render_share_card_svg(persona: dict, scores: dict, personas: dict) -> str:
    """Return a self-contained 1200x630 <svg> share card: persona name +
    tagline on the left, the fingerprint radar (nested, reusing
    `render_fingerprint_svg` verbatim) on the right. Rasterised to PNG by
    the caller (`app/pdf_utils.py` uses it directly as SVG)."""
    w, h = SHARE_CARD_WIDTH, SHARE_CARD_HEIGHT
    name = escape(persona.get('name', ''))
    tagline = escape(persona.get('tagline', ''))

    # `radar_slot` is the actual footprint we want the chart to occupy;
    # render_fingerprint_svg pads its own canvas by _CANVAS_FACTOR, so the
    # logical `size` passed to it must be scaled down to compensate.
    radar_slot = 480
    radar_svg = render_fingerprint_svg(scores, personas, size=radar_slot / _CANVAS_FACTOR)
    radar_x = w - radar_slot - 60
    radar_y = (h - radar_slot) / 2

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="{name} — The Monkey Puzzle">'
        f'<rect width="{w}" height="{h}" fill="#f8f9fa" />'
        f'<rect x="0" y="0" width="14" height="{h}" fill="#2e7d32" />'
        f'<text x="70" y="90" font-family="Arial,sans-serif" font-size="22" '
        f'fill="#6c757d" letter-spacing="1">THE MONKEY PUZZLE</text>'
        f'<text x="70" y="230" font-family="Arial,sans-serif" font-size="28" '
        f'fill="#6c757d">Your sustainable who:</text>'
        f'<text x="70" y="300" font-family="Arial,sans-serif" font-size="56" '
        f'font-weight="700" fill="#212529">{name}</text>'
        f'<text x="70" y="360" font-family="Arial,sans-serif" font-size="26" '
        f'fill="#495057">{tagline}</text>'
        f'<g transform="translate({radar_x:.1f},{radar_y:.1f})">'
        + radar_svg
        + '</g>'
        + '</svg>'
    )
