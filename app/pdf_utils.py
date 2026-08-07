"""PDF generation for The Monkey Puzzle (Phase 5).

Renders `templates/pdf/result.html` via WeasyPrint to produce a
downloadable results report — the persona card, matching what's shown on
the result page.

Split into `render_result_html` (cheap) + `html_to_pdf` (expensive,
WeasyPrint) so `survey.download_pdf` (backlog #0022) can hash the rendered
HTML and only run WeasyPrint on a cache miss, via `app/asset_cache.py`.
`generate_result_pdf` stays a thin wrapper over the two, unchanged in
signature, since `app/email_utils.py` renders (and does not cache) the PDF
fresh on every send.

WeasyPrint requires libpango:
  macOS:  brew install pango  (DYLD_LIBRARY_PATH=/opt/homebrew/lib in .flaskenv)
  Linux:  apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0
"""
from flask import render_template
from weasyprint import HTML


def render_result_html(persona: dict, personas: dict, innovation: dict = None,
                        now_next: dict = None, why: str = None, audience: str = None) -> str:
    """Render `templates/pdf/result.html` to an HTML string (the cheap half
    of PDF generation — cheap enough to run on every request so callers can
    hash it as a cache key; see `html_to_pdf` for the expensive half).

    `innovation` (backlog #0002) is the optional {'band', 'score', 'colour'}
    context for the innovation-curve card; None when the survey has no
    innovation_curve config or the submission has no stored band. `now_next`
    (backlog #0007) is the optional {'now', 'next'} context for the Now/Next
    narrative statements card, None when the survey has no now_next config.
    `why` (backlog #0015) is the optional respondent free-text `output: why`
    answer, None when the survey has no `output: why` question or the
    answer is blank/unanswered. `audience` (backlog #0004) is the
    submission's 'individual'/'organisation'/None routing, threaded through
    so the persona card can resolve `description_organisation`.
    """
    return render_template(
        'pdf/result.html',
        persona=persona,
        personas=personas,
        innovation=innovation,
        now_next=now_next,
        why=why,
        audience=audience,
    )


def html_to_pdf(html: str, base_url: str = None) -> bytes:
    """Rasterise an already-rendered result HTML string to PDF bytes via
    WeasyPrint — the expensive half of PDF generation (see `render_result_html`
    for the cheap half). `base_url` should be the Flask request host URL
    (e.g. `request.url_root`) so WeasyPrint can resolve the Bootstrap CDN
    stylesheet.
    """
    return HTML(string=html, base_url=base_url).write_pdf()


def generate_result_pdf(persona: dict, personas: dict, innovation: dict = None,
                         now_next: dict = None, why: str = None, base_url: str = None, audience: str = None) -> bytes:
    """Render the result PDF for a classified submission.

    Thin wrapper around `render_result_html` + `html_to_pdf`, kept for the
    email path (`app/email_utils.py`) which renders (and does not cache) the
    PDF fresh on every send — see those two functions for parameter docs.
    """
    html = render_result_html(persona, personas,
                               innovation=innovation, now_next=now_next, why=why, audience=audience)
    return html_to_pdf(html, base_url=base_url)
