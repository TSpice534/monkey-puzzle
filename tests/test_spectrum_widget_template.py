"""Focused template-level tests for `survey/_question_spectrum.html`,
covering backlog #0013's replacement of the old `<input type=range>` slider
with a horizontal row of clickable boxes (native radios + `:checked`-sibling
CSS, no JS — mirrors `_question_triangle.html`).

These render the partial in isolation (via the app's Jinja environment, not
the full HTTP route) so we get full control over edge-case label content —
in particular `< > &` characters, which don't happen to appear anywhere in
the real survey content, only apostrophes do. The apostrophe case is
additionally covered against the *real* survey content in
`tests/test_real_survey_e2e.py`.
"""
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


def _input_tag(rendered_html, input_id):
    """The full `<input ...>` tag whose `id="{input_id}"` attribute matches
    exactly (no accidental prefix match against e.g. `q_test_11` when
    looking up `q_test_1`) — used to check a specific radio's `checked`
    state in isolation from its siblings."""
    marker = f'id="{input_id}"'
    marker_start = rendered_html.index(marker)
    tag_start = rendered_html.rindex('<input', 0, marker_start)
    tag_end = rendered_html.index('>', marker_start)
    return rendered_html[tag_start:tag_end]


# ---------------------------------------------------------------------------
# Container / radiogroup structure (happy path)
# ---------------------------------------------------------------------------

def test_container_has_radiogroup_role_and_prompt_as_aria_label(app):
    rendered = _render(app, options=[{'label': 'Low'}, {'label': 'High'}])
    assert 'role="radiogroup"' in rendered
    assert 'aria-label="Test prompt"' in rendered


def test_one_radio_input_per_option_with_correct_name_and_value(app):
    rendered = _render(
        app,
        options=[{'label': 'First'}, {'label': 'Second'}, {'label': 'Third'}],
        question_id='q_test',
    )
    assert rendered.count('type="radio"') == 3
    assert rendered.count('name="q_test"') == 3
    for i in range(3):
        assert f'id="q_test_{i}"' in rendered
        assert f'value="{i}"' in rendered


def test_old_slider_markup_is_entirely_absent(app):
    rendered = _render(
        app,
        options=[
            {'label': 'Start'},
            {'label': 'Intermediate position', 'unlabelled': True},
            {'label': 'End'},
        ],
        saved_value=1,
    )
    assert 'type="range"' not in rendered
    assert 'data-labels' not in rendered
    assert 'form-range' not in rendered
    assert '_current_label' not in rendered


# ---------------------------------------------------------------------------
# Labelled options render full boxes
# ---------------------------------------------------------------------------

def test_labelled_option_renders_full_box_with_visible_text(app):
    rendered = _render(app, options=[{'label': 'Low'}, {'label': 'High'}])
    # Each label box carries the base spectrum-node class but not the mix
    # variant, and shows its label text visibly.
    assert re.search(r'class="spectrum-node"[^>]*for="q_test_0"', rendered)
    assert 'Low' in rendered
    assert 'High' in rendered


# ---------------------------------------------------------------------------
# Unlabelled options render small "mix" boxes between their neighbours
# ---------------------------------------------------------------------------

def test_unlabelled_option_renders_mix_box_between_its_neighbours(app):
    rendered = _render(
        app,
        options=[
            {'label': 'Start'},
            {'label': 'Intermediate position', 'unlabelled': True},
            {'label': 'End'},
        ],
        saved_value=1,
    )
    assert re.search(r'class="spectrum-node spectrum-node--mix"[^>]*for="q_test_1"', rendered)
    # The unlabelled option's own placeholder label must never be visible.
    assert 'Intermediate position' not in rendered
    # A visually-hidden span names both flanking labelled options.
    match = re.search(r'<span class="visually-hidden">(.*?)</span>', rendered)
    assert match, 'expected a visually-hidden flanking-label span on the mix box'
    assert 'Start' in match.group(1)
    assert 'End' in match.group(1)


def test_two_unlabelled_options_each_name_their_own_neighbours(app):
    """Mirrors the real `motivation` question shape: 5 options, indices 1
    and 3 unlabelled, each naming the two labelled options either side of
    it (not the far ones)."""
    rendered = _render(
        app,
        options=[
            {'label': 'Alpha'},
            {'label': 'Mix 1', 'unlabelled': True},
            {'label': 'Beta'},
            {'label': 'Mix 2', 'unlabelled': True},
            {'label': 'Gamma'},
        ],
    )
    spans = re.findall(r'<span class="visually-hidden">(.*?)</span>', rendered)
    assert len(spans) == 2
    assert 'Alpha' in spans[0] and 'Beta' in spans[0] and 'Gamma' not in spans[0]
    assert 'Beta' in spans[1] and 'Gamma' in spans[1] and 'Alpha' not in spans[1]


# ---------------------------------------------------------------------------
# saved_value re-checks the correct radio (both full and mix boxes)
# ---------------------------------------------------------------------------

def test_no_saved_value_checks_nothing(app):
    rendered = _render(app, options=[{'label': 'First'}, {'label': 'Second'}], saved_value=None)
    assert 'checked' not in rendered


def test_saved_value_checks_only_the_matching_full_box_radio(app):
    rendered = _render(
        app,
        options=[{'label': 'First'}, {'label': 'Second'}, {'label': 'Third'}],
        saved_value=2,
    )
    assert 'checked' in _input_tag(rendered, 'q_test_2')
    assert 'checked' not in _input_tag(rendered, 'q_test_0')
    assert 'checked' not in _input_tag(rendered, 'q_test_1')
    assert rendered.count('checked') == 1


def test_saved_value_checks_the_matching_mix_box_radio(app):
    """Selecting an unlabelled between-stop (e.g. motivation index 1) must
    re-check that mix box's radio on revisit, same as any full box."""
    rendered = _render(
        app,
        options=[
            {'label': 'Start'},
            {'label': 'Intermediate position', 'unlabelled': True},
            {'label': 'End'},
        ],
        saved_value=1,
    )
    assert 'checked' in _input_tag(rendered, 'q_test_1')
    assert 'checked' not in _input_tag(rendered, 'q_test_0')
    assert 'checked' not in _input_tag(rendered, 'q_test_2')
    assert rendered.count('checked') == 1


# ---------------------------------------------------------------------------
# Audience-aware wording
# ---------------------------------------------------------------------------

def test_organisation_audience_prefers_label_organisation_in_full_box(app):
    rendered = _render(
        app,
        options=[{'label': 'We/I individual wording', 'label_organisation': 'We organisation wording'}],
        audience='organisation',
    )
    assert 'We organisation wording' in rendered
    assert 'We/I individual wording' not in rendered


def test_individual_audience_uses_label_even_when_label_organisation_present(app):
    rendered = _render(
        app,
        options=[{'label': 'We/I individual wording', 'label_organisation': 'We organisation wording'}],
        audience='individual',
    )
    assert 'We/I individual wording' in rendered
    assert 'We organisation wording' not in rendered


def test_unrouted_audience_none_defaults_to_label(app):
    rendered = _render(
        app,
        options=[{'label': 'We/I individual wording', 'label_organisation': 'We organisation wording'}],
        audience=None,
    )
    assert 'We/I individual wording' in rendered
    assert 'We organisation wording' not in rendered


def test_organisation_audience_wording_also_applies_inside_mix_box_span(app):
    rendered = _render(
        app,
        options=[
            {'label': 'Start', 'label_organisation': 'Org start'},
            {'label': 'Intermediate position', 'unlabelled': True},
            {'label': 'End', 'label_organisation': 'Org end'},
        ],
        audience='organisation',
    )
    match = re.search(r'<span class="visually-hidden">(.*?)</span>', rendered)
    assert match
    assert 'Org start' in match.group(1)
    assert 'Org end' in match.group(1)
    # The individual-track wording must not leak in alongside the org wording.
    assert 'Start' not in match.group(1)
    assert 'End' not in match.group(1)


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
    )
    assert 'Only the individual label exists' in rendered


# ---------------------------------------------------------------------------
# Special-character escaping (single HTML-entity escaping, no double-escape)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('raw_label, expected_fragment', [
    ("It's a trick question", 'It&#39;s a trick question'),
    ('Fish & chips', 'Fish &amp; chips'),
    ('<script>alert(1)</script>', '&lt;script&gt;alert(1)&lt;/script&gt;'),
    ('1 < 2', '1 &lt; 2'),
    ('2 > 1', '2 &gt; 1'),
])
def test_special_characters_render_with_normal_single_escaping_in_box_text(app, raw_label, expected_fragment):
    rendered = _render(app, options=[{'label': raw_label}, {'label': 'Other'}])
    assert expected_fragment in rendered
    # No double-escaping (e.g. `&amp;#39;` or `&amp;amp;`).
    assert '&amp;#39;' not in rendered
    assert '&amp;amp;' not in rendered
    assert '&amp;lt;' not in rendered
    assert '&amp;gt;' not in rendered
