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

# Certificate download image (backlog #0030) — square, not the og:image
# aspect ratio, since this is posted to LinkedIn as a native image, not
# consumed as a link-preview thumbnail. LinkedIn renders square images at
# full feed width, so square reads bigger/more visible in-feed than 1200x630.
CERTIFICATE_WIDTH = 1200
CERTIFICATE_HEIGHT = 1200


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


def render_certificate_svg(persona: dict, band: str = None, band_colour: str = None) -> str:
    """Return a self-contained 1200x1200 <svg> "certificate": eyebrow, "Your
    sustainable who:" lead-in, persona name and tagline, and (when a band is
    given) the innovation-curve band named as text plus a small colour
    swatch — all centred inside an inset frame stroked in the accent colour
    (`band_colour` when given, else `--brand-primary`). Rasterised to PNG by
    the caller (`app/survey/routes.py::download_certificate`), same as
    `render_share_card_svg`. Backlog #0030 — the certificate is square
    (unlike the 1200x630 share card) because it's posted to LinkedIn as a
    native image, not consumed as a link-preview thumbnail."""
    w, h = CERTIFICATE_WIDTH, CERTIFICATE_HEIGHT
    name = escape(persona.get('name', ''))
    tagline = escape(persona.get('tagline', ''))
    accent = band_colour if band_colour else '#2e7d32'

    aria_label = f'{name} — The Monkey Puzzle certificate'
    band_line = ''
    if band:
        band_text = escape(band)
        aria_label += f', Innovation curve: {band_text}'
        band_line = (
            f'<text x="600" y="780" text-anchor="middle" font-family="Arial,sans-serif" '
            f'font-size="28" fill="#495057">Innovation curve: {band_text}</text>'
            f'<rect x="560" y="805" width="80" height="20" rx="4" fill="{accent}" />'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="{aria_label}">'
        f'<rect width="{w}" height="{h}" fill="#f8f9fa" />'
        f'<rect x="48" y="48" width="{w - 96}" height="{h - 96}" rx="24" '
        f'fill="none" stroke="{accent}" stroke-width="6" />'
        f'<text x="600" y="200" text-anchor="middle" font-family="Arial,sans-serif" '
        f'font-size="30" fill="#6c757d" letter-spacing="3">THE MONKEY PUZZLE</text>'
        f'<text x="600" y="430" text-anchor="middle" font-family="Arial,sans-serif" '
        f'font-size="36" fill="#6c757d">Your sustainable who:</text>'
        f'<text x="600" y="560" text-anchor="middle" font-family="Arial,sans-serif" '
        f'font-size="84" font-weight="700" fill="#212529">{name}</text>'
        f'<text x="600" y="650" text-anchor="middle" font-family="Arial,sans-serif" '
        f'font-size="34" fill="#495057">{tagline}</text>'
        + band_line
        + '</svg>'
    )


UNHIGHLIGHTED_BAR_OPACITY = 0.35

_LABEL_CHAR_WIDTH_RATIO = 0.55   # conservative average Arial advance width, in em
_LABEL_MIN_FONT_SIZE = 8.0       # floor for the shrink-to-fit pass
_LABEL_MIN_GAP = 6.0             # minimum px between two adjacent labels


def _estimate_text_width(text: str, font_size: float) -> float:
    """Rough px width of `text` at `font_size` — there is no font-metrics API
    available in a pure-Python SVG generator, so this deliberately over-estimates."""
    return len(text) * font_size * _LABEL_CHAR_WIDTH_RATIO


def _layout_band_labels(entries, width, base_font_size):
    """entries: list of (centre_x, name) sorted ascending by centre_x.
    Returns (font_size, [(x, name), ...]) in the same order — x values are the
    final `text-anchor="middle"` anchors, nudged so no two label boxes overlap
    and every box stays inside [0, width] when the labels fit at all."""
    names = [name for _, name in entries]
    centres = [centre for centre, _ in entries]
    n = len(entries)

    font_size = base_font_size
    widths = [_estimate_text_width(name, font_size) for name in names]
    while (
        font_size > _LABEL_MIN_FONT_SIZE
        and sum(widths) + _LABEL_MIN_GAP * (n - 1) > width
    ):
        font_size -= 0.5
        widths = [_estimate_text_width(name, font_size) for name in names]
    font_size = max(font_size, _LABEL_MIN_FONT_SIZE)
    widths = [_estimate_text_width(name, font_size) for name in names]

    x = list(centres)

    for i in range(n):
        if i == 0:
            lower = widths[i] / 2
        else:
            lower = x[i - 1] + widths[i - 1] / 2 + _LABEL_MIN_GAP + widths[i] / 2
        x[i] = max(x[i], lower)

    for i in range(n - 1, -1, -1):
        if i == n - 1:
            upper = width - widths[i] / 2
        else:
            upper = x[i + 1] - widths[i + 1] / 2 - _LABEL_MIN_GAP - widths[i] / 2
        x[i] = min(x[i], upper)

    return font_size, list(zip(x, names))


def render_innovation_curve_svg(score, bands, width: int = 640, height: int = 240) -> str:
    """Return an inline <svg> string: Rogers' diffusion-of-innovation bell
    curve rendered as equal-width bars, one per whole score point across
    `bands`' full range (16 bars for the real survey's 0–15 range), with
    heights following a symmetric Gaussian envelope so the silhouette reads
    as a bell curve/hump, and the respondent's exact score highlighted in
    its band's full colour at full opacity (every other bar keeps its bold
    band colour but is rendered at `UNHIGHLIGHTED_BAR_OPACITY`).
    Bars are drawn Innovators-left, Laggards-right (highest score first) to
    match the reference diffusion diagram.

    Band-name labels are positioned by a collision-aware layout pass
    (`_layout_band_labels`), left-to-right by band centre, with a font-size
    shrink-to-fit fallback (floor `_LABEL_MIN_FONT_SIZE`) before nudging
    overlapping labels apart — never truncated/ellipsised. If the labels
    still can't all fit inside `[0, width]` even at the font-size floor, the
    leftmost label may be pushed slightly past `x = 0`; this doesn't happen
    for the real survey's bands.

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
    label_y = height - label_area * 0.3
    entries = sorted(
        (
            ((band_spans[band['name']][0] + band_spans[band['name']][1]) / 2, band['name'])
            for band in bands
            if band['name'] in band_spans
        ),
        key=lambda entry: entry[0],
    )
    label_font_size, positioned_labels = _layout_band_labels(entries, width, width * 0.018)
    labels_svg = [
        f'<text x="{x:.2f}" y="{label_y:.2f}" text-anchor="middle" '
        f'font-family="Arial,sans-serif" font-size="{label_font_size:.1f}" '
        f'fill="#495057">{escape(name)}</text>'
        for x, name in positioned_labels
    ]

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
