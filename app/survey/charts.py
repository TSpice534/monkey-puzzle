"""Inline-SVG charts: the radar ("fingerprint") chart over the nine
personas, the OpenGraph share card, and the innovation-curve bell chart.

Adapts the trig/inline-SVG style of Donut Toolkit's
`pdf_utils.py::_generate_donut_svg` — hand-built SVG, no JS, no external
assets, so it renders unaffected by the CSP. Designed as reusable pure
functions so every surface (web, PDF, share image) can call the same
generator.
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


UNHIGHLIGHTED_BAR_OPACITY = 0.35


def render_innovation_curve_svg(score, bands, width: int = 640, height: int = 240) -> str:
    """Return an inline <svg> string: Rogers' diffusion-of-innovation bell
    curve rendered as equal-width bars, one per whole score point across
    `bands`' full range (21 bars for the real survey's 0–20 range), with
    heights following a symmetric Gaussian envelope so the silhouette reads
    as a bell curve/hump, and the respondent's exact score highlighted in
    its band's full colour at full opacity (every other bar keeps its bold
    band colour but is rendered at `UNHIGHLIGHTED_BAR_OPACITY`).
    Bars are drawn Innovators-left, Laggards-right (highest score first) to
    match the reference diffusion diagram.

    Styled on `render_fingerprint_svg`: pure function, self-contained <svg>,
    `role="img"` + `aria-label` (score and band name are always named in
    text, never colour alone), `escape()` for any text, empty-input guard.
    """
    if not bands:
        return ''

    lo = min(b['min'] for b in bands)
    hi = max(b['max'] for b in bands)
    points = list(range(lo, hi + 1))
    n = len(points)

    def _band_for(p):
        return next((b for b in bands if b['min'] <= p <= b['max']), None)

    clamped_score = None
    if score is not None:
        clamped_score = max(lo, min(hi, score))
    highlighted_band = _band_for(clamped_score) if clamped_score is not None else None

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    label_area = height * 0.14      # bottom strip reserved for band-name labels
    top_pad = height * 0.06         # headroom above the tallest bar
    plot_height = height - label_area - top_pad
    baseline_y = height - label_area

    bar_slot = width / n
    bar_gap = bar_slot * 0.15
    bar_width = bar_slot - bar_gap

    center = (n - 1) / 2
    sigma = n / 5
    min_h = 0.18 * plot_height
    max_h = plot_height

    # ------------------------------------------------------------------
    # Bars — descending score order so the leftmost bar is the top score
    # (Innovators) and the rightmost is score 0 (Laggards), matching the
    # reference diffusion diagram.
    # ------------------------------------------------------------------
    bars_svg = []
    band_spans = {}  # band name -> [min_x, max_x] spanned by its bars
    for i, p in enumerate(sorted(points, reverse=True)):
        band = _band_for(p)
        colour = band['colour'] if band else '#adb5bd'
        is_highlight = clamped_score is not None and p == clamped_score
        opacity = 1 if is_highlight else UNHIGHLIGHTED_BAR_OPACITY

        bar_h = min_h + (max_h - min_h) * math.exp(-((i - center) ** 2) / (2 * sigma ** 2))
        x = i * bar_slot + bar_gap / 2
        y = baseline_y - bar_h
        bars_svg.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_h:.2f}" '
            f'fill="{colour}" fill-opacity="{opacity}" />'
        )

        if band is not None:
            span = band_spans.setdefault(band['name'], [x, x + bar_width])
            span[0] = min(span[0], x)
            span[1] = max(span[1], x + bar_width)

    # ------------------------------------------------------------------
    # Section labels — one per band, centred under its span of bars
    # ------------------------------------------------------------------
    label_font_size = width * 0.018
    label_y = height - label_area * 0.3
    labels_svg = []
    for band in bands:
        span = band_spans.get(band['name'])
        if span is None:
            continue
        label_x = (span[0] + span[1]) / 2
        labels_svg.append(
            f'<text x="{label_x:.2f}" y="{label_y:.2f}" text-anchor="middle" '
            f'font-family="Arial,sans-serif" font-size="{label_font_size:.1f}" '
            f'fill="#495057">{escape(band["name"])}</text>'
        )

    # ------------------------------------------------------------------
    # Root <svg> + accessible label — always names the score and band,
    # never relies on colour alone.
    # ------------------------------------------------------------------
    if score is None:
        aria_text = 'Innovation curve — a bar for each possible score, none highlighted.'
    elif highlighted_band is not None:
        aria_text = f'Innovation curve — you scored {score} of {hi} ({highlighted_band["name"]}).'
    else:
        aria_text = f'Innovation curve — you scored {score} of {hi}.'

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(aria_text)}">'
        + ''.join(bars_svg)
        + ''.join(labels_svg)
        + '</svg>'
    )
