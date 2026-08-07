"""Inline-SVG charts: the OpenGraph share card and the innovation-curve
bell chart.

Adapts the trig/inline-SVG style of Donut Toolkit's
`pdf_utils.py::_generate_donut_svg` — hand-built SVG, no JS, no external
assets, so it renders unaffected by the CSP. Designed as reusable pure
functions so every surface (web, PDF, share image) can call the same
generator.
"""
import math
from xml.sax.saxutils import escape


# Standard OpenGraph image size (1200x630) so LinkedIn/Twitter/Facebook
# crawlers render a full, uncropped preview.
SHARE_CARD_WIDTH = 1200
SHARE_CARD_HEIGHT = 630


def render_share_card_svg(persona: dict) -> str:
    """Return a self-contained 1200x630 <svg> share card: eyebrow, "Your
    sustainable who:" lead-in, persona name, and tagline, left-anchored and
    vertically balanced across the full card. Rasterised to PNG by the
    caller (`app/pdf_utils.py` uses it directly as SVG)."""
    w, h = SHARE_CARD_WIDTH, SHARE_CARD_HEIGHT
    name = escape(persona.get('name', ''))
    tagline = escape(persona.get('tagline', ''))

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="{name} — The Monkey Puzzle">'
        f'<rect width="{w}" height="{h}" fill="#f8f9fa" />'
        f'<rect x="0" y="0" width="14" height="{h}" fill="#2e7d32" />'
        f'<text x="70" y="100" font-family="Arial,sans-serif" font-size="26" '
        f'fill="#6c757d" letter-spacing="2">THE MONKEY PUZZLE</text>'
        f'<text x="70" y="285" font-family="Arial,sans-serif" font-size="36" '
        f'fill="#6c757d">Your sustainable who:</text>'
        f'<text x="70" y="390" font-family="Arial,sans-serif" font-size="84" '
        f'font-weight="700" fill="#212529">{name}</text>'
        f'<text x="70" y="470" font-family="Arial,sans-serif" font-size="34" '
        f'fill="#495057">{tagline}</text>'
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
