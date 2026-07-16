"""Focused template-level tests for `survey/_question_spectrum.html`,
covering the merged backlog #0008 (apostrophe/HTML-entity double-escaping
in the JS-driven live label) and #0009 (removal of the static row of every
option label) fix.

These render the partial in isolation (via the app's Jinja environment,
not the full HTTP route) so we get full control over edge-case label
content — in particular `< > &` characters, which don't happen to appear
anywhere in the real survey content, only apostrophes do. The apostrophe
case is additionally covered against the *real* survey content in
`tests/test_real_survey_e2e.py`.
"""
import html as html_lib
import json
import re

import pytest


def _render(app, *, options, audience=None, saved_value=None, question_id='q_test'):
    question = {
        'id': question_id,
        'prompt': 'Test prompt',
        'options': [{**opt, 'index': i} for i, opt in enumerate(options)],
    }
    with app.app_context():
        template = app.jinja_env.get_template('survey/_question_spectrum.html')
        return template.render(question=question, audience=audience, saved_value=saved_value)


def _data_labels_attr_raw(rendered_html):
    """The raw (still-JSON-encoded) text of the data-labels attribute."""
    start = rendered_html.index("data-labels='") + len("data-labels='")
    end = rendered_html.index("'", start)
    return rendered_html[start:end]


def _data_labels(rendered_html):
    return json.loads(_data_labels_attr_raw(rendered_html))


def _current_label_text(rendered_html, question_id):
    """The live-label span's text, HTML-unescaped — i.e. what a browser
    would actually display, since normal single HTML-entity escaping in
    this SSR context is expected and correctly decoded by the browser."""
    match = re.search(
        rf'<span id="{question_id}_current_label">(.*?)</span>', rendered_html, re.DOTALL
    )
    assert match, 'current label span not found in rendered output'
    return html_lib.unescape(match.group(1))


# ---------------------------------------------------------------------------
# #0008 — apostrophe / entity escaping (the actual bug being fixed)
# ---------------------------------------------------------------------------

def test_apostrophe_survives_the_data_labels_json_round_trip(app):
    """The old bug: option_label()'s Markup output (already HTML-escaped,
    e.g. an apostrophe as the literal 6 characters `&#39;`) got fed into
    `tojson`, which re-escaped that already-escaped text — so the browser's
    `JSON.parse` + `textContent` write showed the literal `&#39;` on
    screen. The fix builds `ns.labels` from the raw string instead."""
    rendered = _render(app, options=[
        {'label': "Option that's tricky"},
        {'label': 'Plain option'},
    ])
    raw_attr = _data_labels_attr_raw(rendered)
    assert '&#39;' not in raw_attr, (
        'data-labels attribute still contains the double-escaped entity — '
        'this is the #0008 regression'
    )
    labels = json.loads(raw_attr)
    assert labels[0] == "Option that's tricky"


@pytest.mark.parametrize('raw_label', [
    "It's a trick question",
    'Fish & chips',
    '<script>alert(1)</script>',
    '1 < 2',
    '2 > 1',
])
def test_special_characters_round_trip_correctly_through_data_labels_json(app, raw_label):
    rendered = _render(app, options=[{'label': raw_label}, {'label': 'Other'}])
    labels = _data_labels(rendered)
    assert labels[0] == raw_label
    # None of the HTML-entity forms should leak into the JSON payload —
    # tojson's own \u-escaping is the only encoding applied.
    raw_attr = _data_labels_attr_raw(rendered)
    assert '&#39;' not in raw_attr
    assert '&amp;' not in raw_attr
    assert '&lt;' not in raw_attr
    assert '&gt;' not in raw_attr


@pytest.mark.parametrize('raw_label', [
    "It's a trick question",
    'Fish & chips',
    '<script>alert(1)</script>',
])
def test_current_label_span_displays_the_correct_character_after_browser_unescape(app, raw_label):
    rendered = _render(app, options=[{'label': raw_label}], saved_value=0)
    assert _current_label_text(rendered, 'q_test') == raw_label


# ---------------------------------------------------------------------------
# #0009 — static label row removed, only the live label remains
# ---------------------------------------------------------------------------

def test_static_label_row_is_not_rendered(app):
    rendered = _render(app, options=[{'label': 'Low'}, {'label': 'Mid'}, {'label': 'High'}])
    assert 'd-flex justify-content-between small text-muted' not in rendered


def test_only_one_span_is_rendered_the_live_label(app):
    rendered = _render(app, options=[{'label': 'Low'}, {'label': 'Mid'}, {'label': 'High'}])
    assert rendered.count('<span') == 1
    assert '_current_label' in rendered


# ---------------------------------------------------------------------------
# Initial value on page load (happy path)
# ---------------------------------------------------------------------------

def test_fresh_render_with_no_saved_value_defaults_to_index_zero(app):
    rendered = _render(app, options=[{'label': 'First'}, {'label': 'Second'}], saved_value=None)
    assert 'value="0"' in rendered
    assert _current_label_text(rendered, 'q_test') == 'First'


def test_saved_value_selects_the_matching_initial_label(app):
    rendered = _render(
        app,
        options=[{'label': 'First'}, {'label': 'Second'}, {'label': 'Third'}],
        saved_value=2,
    )
    assert 'value="2"' in rendered
    assert _current_label_text(rendered, 'q_test') == 'Third'


# ---------------------------------------------------------------------------
# Unlabelled between-stop options
# ---------------------------------------------------------------------------

def test_unlabelled_option_renders_an_empty_live_label_not_undefined(app):
    rendered = _render(
        app,
        options=[
            {'label': 'Start'},
            {'label': 'Intermediate position', 'unlabelled': True},
            {'label': 'End'},
        ],
        saved_value=1,
    )
    assert _current_label_text(rendered, 'q_test') == ''
    assert '<span id="q_test_current_label"></span>' in rendered
    assert 'undefined' not in rendered
    assert 'Intermediate position' not in rendered
    # The unlabelled option's placeholder text is still absent from the
    # data-labels JSON too, it should serialise to an empty string.
    assert _data_labels(rendered)[1] == ''


# ---------------------------------------------------------------------------
# Audience-aware wording
# ---------------------------------------------------------------------------

def test_organisation_audience_prefers_label_organisation(app):
    rendered = _render(
        app,
        options=[{'label': 'We/I individual wording', 'label_organisation': 'We organisation wording'}],
        audience='organisation',
        saved_value=0,
    )
    assert _current_label_text(rendered, 'q_test') == 'We organisation wording'


def test_individual_audience_uses_label_even_when_label_organisation_present(app):
    rendered = _render(
        app,
        options=[{'label': 'We/I individual wording', 'label_organisation': 'We organisation wording'}],
        audience='individual',
        saved_value=0,
    )
    assert _current_label_text(rendered, 'q_test') == 'We/I individual wording'


def test_unrouted_audience_none_defaults_to_label(app):
    rendered = _render(
        app,
        options=[{'label': 'We/I individual wording', 'label_organisation': 'We organisation wording'}],
        audience=None,
        saved_value=0,
    )
    assert _current_label_text(rendered, 'q_test') == 'We/I individual wording'


# ---------------------------------------------------------------------------
# Failure / malformed-input case
# ---------------------------------------------------------------------------

def test_option_missing_label_organisation_key_entirely_falls_back_without_erroring(app):
    """Not just a falsy/None `label_organisation` — the key can be entirely
    absent from the option dict (as it is for several real survey options).
    The template must not raise and must still fall back to `label`."""
    rendered = _render(
        app,
        options=[{'label': 'Only the individual label exists'}],  # no 'label_organisation' key at all
        audience='organisation',
        saved_value=0,
    )
    assert _current_label_text(rendered, 'q_test') == 'Only the individual label exists'
