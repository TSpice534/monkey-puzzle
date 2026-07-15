"""PDF generation for The Monkey Puzzle (Phase 5).

Renders `templates/pdf/result.html` via WeasyPrint to produce a
downloadable results report — the persona card + fingerprint radar,
reusing the same `render_fingerprint_svg` output shown on the result
page and embedded in the share image/email.

WeasyPrint requires libpango:
  macOS:  brew install pango  (DYLD_LIBRARY_PATH=/opt/homebrew/lib in .flaskenv)
  Linux:  apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0
"""
from flask import render_template
from weasyprint import HTML


def generate_result_pdf(persona: dict, personas: dict, fingerprint_svg: str, innovation: dict = None,
                         base_url: str = None) -> bytes:
    """Render the result PDF for a classified submission.

    base_url should be the Flask request host URL (e.g. request.url_root)
    so WeasyPrint can resolve the Bootstrap CDN stylesheet. `innovation`
    (backlog #0002) is the optional {'band', 'score', 'colour'} context for
    the innovation-curve card; None when the survey has no innovation_curve
    config or the submission has no stored band.
    """
    html = render_template(
        'pdf/result.html',
        persona=persona,
        personas=personas,
        fingerprint_svg=fingerprint_svg,
        innovation=innovation,
    )
    return HTML(string=html, base_url=base_url).write_pdf()
