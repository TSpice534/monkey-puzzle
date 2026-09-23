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
    (`band_colour` when given, else `--brand-primary`), with a site/URL
    footer line near the bottom of the frame so a downloaded/reshared PNG
    still carries a CTA once it's separated from the caption. Rasterised to
    PNG by the caller (`app/survey/routes.py::download_certificate`), same
    as `render_share_card_svg`. Backlog #0030 — the certificate is square
    (unlike the 1200x630 share card) because it's posted to LinkedIn as a
    native image, not consumed as a link-preview thumbnail.

    Vertical rhythm is deliberately different between the with-band and
    without-band cases: the frame runs 48->1152, and simply reusing the
    with-band y-coordinates when `band` is omitted would leave an even
    bigger dead zone where the band line/swatch would have sat. Instead
    each case spaces its own content across the full frame so both read as
    a balanced, designed certificate rather than "content that ran out"."""
    w, h = CERTIFICATE_WIDTH, CERTIFICATE_HEIGHT
    name = escape(persona.get('name', ''))
    tagline = escape(persona.get('tagline', ''))
    accent = band_colour if band_colour else '#2e7d32'

    aria_label = f'{name} — The Monkey Puzzle certificate'
    band_line = ''
    if band:
        band_text = escape(band)
        aria_label += f', Innovation curve: {band_text}'
        eyebrow_y, leadin_y, name_y, tagline_y, footer_y = 200, 340, 520, 610, 980
        band_line = (
            f'<text x="600" y="740" text-anchor="middle" font-family="Arial,sans-serif" '
            f'font-size="28" fill="#495057">Innovation curve: {band_text}</text>'
            f'<rect x="560" y="765" width="80" height="22" rx="4" fill="{accent}" />'
        )
    else:
        eyebrow_y, leadin_y, name_y, tagline_y, footer_y = 220, 400, 620, 760, 990

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="{aria_label}">'
        f'<rect width="{w}" height="{h}" fill="#f8f9fa" />'
        f'<rect x="48" y="48" width="{w - 96}" height="{h - 96}" rx="24" '
        f'fill="none" stroke="{accent}" stroke-width="6" />'
        f'<text x="600" y="{eyebrow_y}" text-anchor="middle" font-family="Arial,sans-serif" '
        f'font-size="30" fill="#6c757d" letter-spacing="3">THE MONKEY PUZZLE</text>'
        f'<text x="600" y="{leadin_y}" text-anchor="middle" font-family="Arial,sans-serif" '
        f'font-size="36" fill="#6c757d">Your sustainable who:</text>'
        f'<text x="600" y="{name_y}" text-anchor="middle" font-family="Arial,sans-serif" '
        f'font-size="84" font-weight="700" fill="#212529">{name}</text>'
        f'<text x="600" y="{tagline_y}" text-anchor="middle" font-family="Arial,sans-serif" '
        f'font-size="34" fill="#495057">{tagline}</text>'
        + band_line
        + f'<text x="600" y="{footer_y}" text-anchor="middle" font-family="Arial,sans-serif" '
        f'font-size="22" fill="#6c757d" letter-spacing="1">tomspice.co.uk/monkey-puzzle</text>'
        + '</svg>'
    )


UNHIGHLIGHTED_BAR_OPACITY = 0.35


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

    Band names are not drawn inside the SVG — they're rendered as an HTML
    legend below the chart (`app/templates/survey/_result_innovation.html`,
    backlog #0040) so they keep normal browser text scaling instead of being
    downscaled along with the responsive SVG viewBox. The SVG's `aria-label`
    still names the score and band.

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
    bottom_pad = height * 0.04       # small breathing room below the bars
    top_pad = height * 0.06          # headroom above the tallest bar
    plot_height = height - bottom_pad - top_pad
    baseline_y = height - bottom_pad

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
        + '</svg>'
    )
