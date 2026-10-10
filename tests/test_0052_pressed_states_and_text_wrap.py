"""Backlog #0052: pressed states (reduced-motion safe) and text-wrap polish."""
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEME_CSS_PATH = os.path.join(REPO_ROOT, 'app', 'static', 'css', 'theme.css')
NO_PREF = '@media (prefers-reduced-motion: no-preference)'
NO_PREF_RE = r'@media \(prefers-reduced-motion: no-preference\) \{(.*?)\} \}'


def _read(*parts):
    with open(os.path.join(REPO_ROOT, *parts), encoding='utf-8') as f:
        return f.read()


def _css():
    return re.sub(r'\s+', ' ', _read('app', 'static', 'css', 'theme.css'))


def _block():
    return re.search(NO_PREF_RE, _css()).group(1)


def test_no_preference_block_once_and_before_mobile():
    css = _css()
    assert css.count(NO_PREF) == 1
    assert css.index(NO_PREF) < css.index('@media (max-width: 767.98px)')


def test_active_rules_scale_inside_block():
    block = _block()
    for sel in ('.option-card:active', '.spectrum-node:active',
                '.grid-cell--result[tabindex="0"]:active', '.btn:active'):
        assert sel in block
    m = re.search(r'\.option-card:active,.*?\.btn:active \{([^}]*)\}', block)
    assert 'transform: scale(0.98)' in m.group(1)
    assert re.search(
        r'\.triangle-node:active \{ transform: translate\(-50%, -50%\) scale\(0\.98\);',
        block)


def test_no_scale_or_active_transform_outside_block():
    css = _css()
    outside = re.sub(NO_PREF_RE, '', css, count=1)
    assert 'scale(0.98)' not in outside
    for m in re.finditer(r'([^{}]*:active[^{}]*) \{([^}]*)\}', outside):
        assert 'transform' not in m.group(2)


def test_transitions_are_explicit():
    css = _css()
    assert 'transition: all' not in css
    decls = re.findall(r'transition:([^;]*);', _block())
    assert decls
    for d in decls:
        assert 'transform' in d
        assert 'all' not in d.split()


def test_reduce_block_unchanged():
    css = _css()
    assert css.count('@media (prefers-reduced-motion: reduce)') == 1
    m = re.search(r'@media \(prefers-reduced-motion: reduce\) \{(.*?)\} \}', css)
    assert '.persona-badge--reveal { animation: none' in m.group(1)


def test_text_wrap_rules_and_order():
    css = _css()
    pretty = re.search(r':where\(([^)]*)\) \{ text-wrap: pretty;', css)
    balance = re.search(r':where\(([^)]*)\) \{ text-wrap: balance;', css)
    assert pretty and balance
    assert 'p' in pretty.group(1).split(', ') and 'li' in pretty.group(1).split(', ')
    assert 'h1' in balance.group(1) and '.h4' in balance.group(1)
    assert pretty.start() < balance.start()


def test_placement_regression_guards():
    css = _css()
    assert css.count('@media (prefers-color-scheme: dark)') == 2
    assert css.count('@media (max-width: 767.98px)') == 1
    assert re.search(r'@media \(max-width: 767\.98px\) \{(.*)\} \}\s*$', css)


def test_pdf_and_email_unaffected():
    for parts in (('app', 'templates', 'pdf', 'result.html'),
                  ('app', 'templates', 'email', 'result.html'),
                  ('app', 'templates', 'email', 'result.txt')):
        raw = _read(*parts)
        assert 'text-wrap' not in raw
        assert ':active' not in raw


def test_design_md_documents_changes():
    design = _read('DESIGN.md')
    assert 'prefers-reduced-motion: no-preference' in design
    assert 'text-wrap' in design
