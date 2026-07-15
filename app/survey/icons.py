"""Inline persona icon SVGs into templates.

A persona's `icon` (content/survey.yaml) is a path relative to the Flask
static folder (e.g. 'icons/developer.svg'). We inline the file's SVG markup
directly — same approach as the fingerprint radar — so it renders identically
in the browser and in the WeasyPrint PDF without any HTTP round-trip or CSP
img-src grant. Content is trusted (owned by Rob/Andrew), not user input.
"""
import os

from flask import current_app
from markupsafe import Markup

_cache = {}  # keyed by static-relative icon path -> raw SVG string


def persona_icon(persona: dict) -> Markup:
    """Return the inlined SVG markup for `persona`, or empty Markup if the
    persona has no `icon` or the file is missing (renders nothing, never errors)."""
    icon = (persona or {}).get('icon')
    if not icon:
        return Markup('')
    if icon not in _cache:
        path = os.path.join(current_app.static_folder, icon)
        try:
            with open(path, 'r', encoding='utf-8') as fh:
                _cache[icon] = fh.read().strip()
        except OSError:
            _cache[icon] = ''
    return Markup(_cache[icon])
