"""Unit tests for `app/asset_cache.py` (backlog #0022) — the on-disk,
content-addressed cache helper used by `share_image` and `download_pdf`.

`tests/test_sharing.py` already covers the cache from the route level (a
second request for the same submission skips the expensive render). This
file drives `get_or_render` directly against an isolated `tmp_path` cache
dir so it can exercise the edge cases that aren't reachable — or aren't
obviously distinguishable from a route-level test — through HTTP: distinct
cache keys never colliding, the atomic-write/temp-file path, and the two
halves of the error-handling contract (a genuine render error propagates;
a cache I/O failure never does).
"""
import hashlib
import logging
import os

import pytest

from app.asset_cache import get_or_render


def _digest(key_material: str) -> str:
    return hashlib.sha256(key_material.encode('utf-8')).hexdigest()


# ---------------------------------------------------------------------------
# happy path
# ---------------------------------------------------------------------------

def test_get_or_render_cache_miss_renders_and_persists_bytes(app, tmp_path):
    app.config['ASSET_CACHE_DIR'] = str(tmp_path)

    with app.app_context():
        result = get_or_render('some-input', '.bin', lambda: b'rendered-bytes')

    assert result == b'rendered-bytes'
    path = tmp_path / (_digest('some-input') + '.bin')
    assert path.read_bytes() == b'rendered-bytes'


def test_get_or_render_cache_hit_skips_render_entirely(app, tmp_path):
    app.config['ASSET_CACHE_DIR'] = str(tmp_path)
    calls = []

    def render():
        calls.append(1)
        return b'hello-bytes'

    with app.app_context():
        first = get_or_render('same-input', '.bin', render)
        second = get_or_render('same-input', '.bin', render)

    assert first == second == b'hello-bytes'
    assert len(calls) == 1  # the whole point of the cache


# ---------------------------------------------------------------------------
# cache key collision avoidance
# ---------------------------------------------------------------------------

def test_get_or_render_different_key_material_never_collides(app, tmp_path):
    """Two distinct render inputs (e.g. two different personas' SVGs) must
    land on two distinct cache files, each returning its own bytes — not
    one clobbering or shadowing the other."""
    app.config['ASSET_CACHE_DIR'] = str(tmp_path)
    calls = []

    def render_a():
        calls.append('a')
        return b'AAAA'

    def render_b():
        calls.append('b')
        return b'BBBB'

    with app.app_context():
        result_a = get_or_render('input-a', '.bin', render_a)
        result_b = get_or_render('input-b', '.bin', render_b)
        # Re-fetch both — each must still resolve to its own cached bytes,
        # not the other's, and neither should re-render.
        result_a_again = get_or_render('input-a', '.bin', render_a)
        result_b_again = get_or_render('input-b', '.bin', render_b)

    assert result_a == result_a_again == b'AAAA'
    assert result_b == result_b_again == b'BBBB'
    assert calls == ['a', 'b']  # only the two initial misses rendered

    files = sorted(os.listdir(tmp_path))
    assert files == sorted([_digest('input-a') + '.bin', _digest('input-b') + '.bin'])


def test_get_or_render_single_character_difference_in_key_material_produces_different_entry(app, tmp_path):
    """Guards against any accidental truncation/normalisation of
    `key_material` before hashing — a near-identical but distinct render
    input (e.g. a persona retune that only changes one field) must not
    collide with the old cached entry."""
    app.config['ASSET_CACHE_DIR'] = str(tmp_path)

    with app.app_context():
        get_or_render('The Inventor', '.bin', lambda: b'old-render')
        get_or_render('The Inventor!', '.bin', lambda: b'new-render')

    files = sorted(os.listdir(tmp_path))
    assert files == sorted([_digest('The Inventor') + '.bin', _digest('The Inventor!') + '.bin'])


# ---------------------------------------------------------------------------
# atomic write / temp-file path
# ---------------------------------------------------------------------------

def test_get_or_render_leaves_no_temp_file_behind_after_a_successful_write(app, tmp_path):
    app.config['ASSET_CACHE_DIR'] = str(tmp_path)

    with app.app_context():
        get_or_render('atomic-write-check', '.bin', lambda: b'payload')

    files = os.listdir(tmp_path)
    assert files == [_digest('atomic-write-check') + '.bin']
    assert not any('.tmp' in name for name in files)


def test_get_or_render_overwrites_via_replace_rather_than_assuming_absence(app, tmp_path):
    """Per the spec's concurrent-writer edge case: the code must not assume
    the destination is still absent by the time it's ready to write (the
    exists-check ran before `render()`). Simulate another worker's write
    landing at the destination path mid-render, then assert our own
    (content-identical-in-practice, but distinguishable here) bytes still
    win via `os.replace` — no `FileExistsError`, no special-casing."""
    app.config['ASSET_CACHE_DIR'] = str(tmp_path)
    digest = _digest('race-key')
    dest = tmp_path / (digest + '.bin')

    def render():
        # "Another worker" finishes first and writes the destination
        # directly while we're still inside our own render() call.
        dest.write_bytes(b'stale-from-other-worker')
        return b'our-correct-bytes'

    with app.app_context():
        result = get_or_render('race-key', '.bin', render)

    assert result == b'our-correct-bytes'
    assert dest.read_bytes() == b'our-correct-bytes'
    assert not any('.tmp' in name for name in os.listdir(tmp_path))


# ---------------------------------------------------------------------------
# error-handling contract
# ---------------------------------------------------------------------------

def test_get_or_render_propagates_a_genuine_render_error(app, tmp_path):
    """A real rendering failure (WeasyPrint/cairosvg raising) must surface
    as a real error, not be swallowed by the cache layer."""
    app.config['ASSET_CACHE_DIR'] = str(tmp_path)

    def boom():
        raise RuntimeError('rendering exploded')

    with app.app_context():
        with pytest.raises(RuntimeError, match='rendering exploded'):
            get_or_render('error-key', '.bin', boom)

    # No partial/orphaned cache entry from the failed attempt.
    assert os.listdir(tmp_path) == []


def test_get_or_render_cache_write_failure_still_returns_rendered_bytes(app, tmp_path, monkeypatch, caplog):
    """A cache-dir I/O failure (can't makedirs/write) must never turn into
    a 500 — the freshly rendered bytes are still returned, with the
    failure only logged."""
    app.config['ASSET_CACHE_DIR'] = str(tmp_path)
    import app.asset_cache as asset_cache_module

    def _boom_makedirs(*args, **kwargs):
        raise OSError('disk is read-only')

    monkeypatch.setattr(asset_cache_module.os, 'makedirs', _boom_makedirs)

    caplog.set_level(logging.ERROR)
    with app.app_context():
        result = get_or_render('write-fail-key', '.bin', lambda: b'rendered-bytes')

    assert result == b'rendered-bytes'
    assert os.listdir(tmp_path) == []  # nothing persisted, but we didn't blow up
    assert 'Failed to write asset cache entry' in caplog.text


@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses file permission checks")
def test_get_or_render_cache_read_failure_falls_through_to_a_fresh_render(app, tmp_path):
    """An unreadable (e.g. permission-denied) existing cache entry must not
    raise — the code should treat it as a miss and re-render."""
    app.config['ASSET_CACHE_DIR'] = str(tmp_path)
    digest = _digest('read-fail-key')
    path = tmp_path / (digest + '.bin')
    path.write_bytes(b'unreadable-stale-content')
    os.chmod(path, 0o000)

    calls = []

    def render():
        calls.append(1)
        return b'fresh-bytes'

    try:
        with app.app_context():
            result = get_or_render('read-fail-key', '.bin', render)
    finally:
        os.chmod(path, 0o644)  # make sure tmp_path cleanup can remove it

    assert result == b'fresh-bytes'
    assert calls == [1]
