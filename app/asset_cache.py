"""Tiny content-addressed on-disk cache for expensive rendered assets
(backlog #0022) — the share-card PNG and result PDF.

Keyed by a SHA-256 hash of the cheap render input (the SVG string for the
PNG; the HTML string + base_url for the PDF), NOT by submission token, so
the cache is self-invalidating: retuning `content/survey.yaml` changes the
rendered SVG/HTML, changes the hash, and produces a fresh render
automatically rather than serving something stale.
"""
import hashlib
import os
import secrets

from flask import current_app


def get_or_render(key_material: str, suffix: str, render) -> bytes:
    """Return cached bytes for `key_material`, rendering (and caching) on a miss.

    `suffix` is the on-disk file extension (e.g. '.png', '.pdf'), used only
    for the cache filename to aid debugging. `render` is a zero-arg callable
    invoked only on a cache miss; its errors are never caught here — a
    genuine render failure should propagate as it does today.

    Caching failures (can't read/write the cache dir) never turn into a
    500 — they're logged and the rendered bytes are returned regardless.
    """
    cache_dir = current_app.config['ASSET_CACHE_DIR']
    digest = hashlib.sha256(key_material.encode('utf-8')).hexdigest()
    path = os.path.join(cache_dir, digest + suffix)

    try:
        with open(path, 'rb') as f:
            return f.read()
    except OSError:
        pass

    data = render()

    try:
        os.makedirs(cache_dir, exist_ok=True)
        tmp_path = path + '.' + secrets.token_hex(8) + '.tmp'
        with open(tmp_path, 'wb') as f:
            f.write(data)
        # Atomic rename — concurrent writers producing the same content is
        # safe, last-writer-wins, since the bytes are identical either way.
        os.replace(tmp_path, path)
    except OSError:
        current_app.logger.exception('Failed to write asset cache entry for %s', path)

    return data
