"""Unit-style tests for the `role_phrase` Jinja macro
(`app/templates/survey/_macros.html`), added for backlog #0028.

Renders the macro directly via the app's Jinja environment (pattern shared
with `test_spectrum_widget_template.py`) with hand-built `personas` dicts, so
we get full control over list length and name content — in particular the
3+ roles (Oxford-comma) branch, which no real persona in `content/
survey.yaml` currently exercises (every `natural_allies`/`friends`/
`necessity` list today has length 1 or 2). The pair/singular branches and the
article rule are already covered end-to-end against real content in
`tests/test_persona_copy_verification.py`; this file exists to close that
one real gap and to pin down the macro's escaping/whitespace contract
in isolation.
"""
import pytest


def _role_phrase(app, persona_ids, personas):
    with app.app_context():
        template = app.jinja_env.get_template('survey/_macros.html')
        return str(template.module.role_phrase(persona_ids, personas))


PERSONAS = {
    'accountant': {'name': 'The Accountant'},
    'implementer': {'name': 'The Implementer'},
    'cooperator': {'name': 'The Cooperator'},
    'inventor': {'name': 'The Inventor'},
    'architect': {'name': 'The Architect'},
    'no_prefix_consonant': {'name': 'Xylophonist'},
    'no_prefix_vowel': {'name': 'Egret'},
    'unsafe': {'name': '<script>alert(1)</script> & Friends'},
}


# ---------------------------------------------------------------------------
# Happy path — the branches already exercised through real content
# ---------------------------------------------------------------------------

def test_two_ids_join_with_and_verbatim_names_no_article(app):
    result = _role_phrase(app, ['implementer', 'cooperator'], PERSONAS)
    assert result == 'The Implementer and The Cooperator'


def test_single_id_strips_the_prefix_and_prepends_article(app):
    result = _role_phrase(app, ['accountant'], PERSONAS)
    assert result == 'an Accountant'


# ---------------------------------------------------------------------------
# The flagged gap — 3+ roles, Oxford-comma join, not present in real data
# ---------------------------------------------------------------------------

def test_three_ids_oxford_comma_join_verbatim_names(app):
    result = _role_phrase(app, ['accountant', 'implementer', 'cooperator'], PERSONAS)
    assert result == 'The Accountant, The Implementer, and The Cooperator'


def test_four_ids_oxford_comma_join_no_dangling_and_no_double_comma(app):
    result = _role_phrase(
        app, ['accountant', 'implementer', 'cooperator', 'inventor'], PERSONAS,
    )
    assert result == 'The Accountant, The Implementer, The Cooperator, and The Inventor'
    # No dangling "and" mid-list, no double comma from the loop/tail join meeting.
    assert ', and and ' not in result
    assert ',,' not in result
    assert result.count(' and ') == 1


# ---------------------------------------------------------------------------
# Edge cases named in the spec
# ---------------------------------------------------------------------------

def test_name_without_the_prefix_passes_through_unchanged_consonant_initial(app):
    result = _role_phrase(app, ['no_prefix_consonant'], PERSONAS)
    assert result == 'a Xylophonist'


def test_name_without_the_prefix_passes_through_unchanged_vowel_initial(app):
    result = _role_phrase(app, ['no_prefix_vowel'], PERSONAS)
    assert result == 'an Egret'


def test_vowel_and_consonant_article_computed_dynamically_across_real_nine(app):
    """Mirrors the spec's table of the real nine personas' expected article,
    guarding against a hardcoded per-persona lookup regressing to something
    that merely happens to pass on today's nine names."""
    vowel_personas = {
        'accountant': {'name': 'The Accountant'},
        'implementer': {'name': 'The Implementer'},
        'inventor': {'name': 'The Inventor'},
        'architect': {'name': 'The Architect'},
        'activist': {'name': 'The Activist'},
        'entrepreneur': {'name': 'The Entrepreneur'},
    }
    consonant_personas = {
        'communicator': {'name': 'The Communicator'},
        'connector': {'name': 'The Connector'},
        'cooperator': {'name': 'The Cooperator'},
    }
    for pid, persona in vowel_personas.items():
        result = _role_phrase(app, [pid], {pid: persona})
        assert result.startswith('an '), f'{pid} -> {result!r}'
    for pid, persona in consonant_personas.items():
        result = _role_phrase(app, [pid], {pid: persona})
        assert result.startswith('a '), f'{pid} -> {result!r}'


# ---------------------------------------------------------------------------
# Whitespace contract — mid-sentence use, no leading/trailing space, so a
# caller's trailing "." sits tight against the output (spec's explicit
# "not `with an Accountant .`" requirement).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('persona_ids', [
    ['accountant'],
    ['implementer', 'cooperator'],
    ['accountant', 'implementer', 'cooperator'],
])
def test_output_has_no_leading_or_trailing_whitespace(app, persona_ids):
    result = _role_phrase(app, persona_ids, PERSONAS)
    assert result == result.strip()


def test_full_stop_sits_tight_against_output_when_concatenated_like_the_template(app):
    result = _role_phrase(app, ['accountant'], PERSONAS)
    sentence = f'Collaborating with {result} would be a good way to improve impact.'
    assert 'Accountant would' in sentence
    assert ' .' not in sentence


# ---------------------------------------------------------------------------
# Failure case — auto-escaping must hold; a name containing HTML/JS must
# never render unescaped, since the macro emits every name through its own
# `{{ }}` and the spec explicitly forbids `| safe` anywhere in this change.
# ---------------------------------------------------------------------------

def test_unsafe_name_content_is_html_escaped_not_rendered_raw(app):
    result = _role_phrase(app, ['unsafe'], PERSONAS)
    assert '<script>' not in result
    assert '&lt;script&gt;' in result
    assert '&amp; Friends' in result


def test_unsafe_name_content_is_html_escaped_in_pair_branch(app):
    result = _role_phrase(app, ['unsafe', 'accountant'], PERSONAS)
    assert '<script>' not in result
    assert '&lt;script&gt;' in result


def test_unsafe_name_content_is_html_escaped_in_three_plus_branch(app):
    result = _role_phrase(app, ['unsafe', 'accountant', 'implementer'], PERSONAS)
    assert '<script>' not in result
    assert '&lt;script&gt;' in result
