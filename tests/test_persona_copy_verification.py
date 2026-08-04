"""Independent verification of backlog #0004 (real persona & innovation-curve
copy, natural_allies/friends/necessity rename, audience-aware description)
against the REAL content/survey.yaml, driven through the Flask test client
exactly as a browser would — complementing (not duplicating) the coder's own
tests in test_real_survey_e2e.py and test_loader.py.

Focus areas independently verified here:
  1. Two-value relationship lists (Communicator) render comma-separated, not
     just the first value — the coder's own tests only exercised Entrepreneur.
  2. The Laggard band's tagline ("You are a Laggard. Wanker.") renders
     byte-for-byte, verbatim, on a real low-scoring submission — reached
     through the actual route flow, not just a hand-built fixture context.
  3. `audience` is None *before* the router question is ever answered (not
     just 'individual' vs 'organisation') — the un-routed edge case must
     still fall back to `description` without crashing.
  4. Persona relationships (natural_allies/friends/necessity) are genuinely
     absent from both email bodies — a regression guard, since this is a
     deliberate pre-existing gap the spec called out as staying that way.
  5. Failure case: the loader must reject an innovation-curve band that is
     missing `tagline` or `description` (required per backlog #0004) — the
     existing `test_innovation_curve_band_missing_field_raises` parametrize
     list was never extended to cover these two new required fields.
"""
import os

import pytest

from app.models import Submission
from app.survey.loader import SurveyConfigError, clear_survey_cache, load_survey

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_SURVEY_PATH = os.path.join(REPO_ROOT, 'content', 'survey.yaml')

INDIVIDUAL = 0
ORGANISATION = 1

STEP_RESPONDENT_TYPE = 1
STEP_MOTIVATION = 2
STEP_AMBITION = 3
STEP_SPACE_TO_PROGRESS = 4
STEP_NEED_MOST = 5
STEP_HAVE_ENOUGH = 6
STEP_PROFILE_GRID = 7
STEP_TOPICS = 8
STEP_SUPPORT_TYPE = 9
STEP_TARGET_GROUPS = 10
STEP_WHY_REASON = 11


@pytest.fixture(autouse=True)
def _use_real_survey(app):
    app.config['SURVEY_PATH'] = REAL_SURVEY_PATH
    clear_survey_cache()
    yield
    clear_survey_cache()


def _start_new(client):
    response = client.get('/survey/start')
    assert response.status_code == 302
    return response.headers['Location'].split('/survey/')[1].split('/step/')[0]


def _complete_survey(client, token, respondent_type_data, motivation='0',
                      ambition='0', space='0', grid='1,1'):
    """Walk steps 2-11 to completion; step 1 (respondent_type) is driven by
    the caller so both the normal and the skipped-router cases can share
    this helper. `why_reason` (step 11, backlog #0015) is now last and its
    POST is what triggers classification."""
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data=respondent_type_data)
    client.post(f'/survey/{token}/step/{STEP_MOTIVATION}', data={} if motivation is None else {'motivation': motivation})
    client.post(f'/survey/{token}/step/{STEP_AMBITION}', data={} if ambition is None else {'ambition': ambition})
    client.post(f'/survey/{token}/step/{STEP_SPACE_TO_PROGRESS}', data={} if space is None else {'space_to_progress': space})
    client.post(f'/survey/{token}/step/{STEP_NEED_MOST}', data={'need_most': '0'})
    client.post(f'/survey/{token}/step/{STEP_HAVE_ENOUGH}', data={'have_enough': '0'})
    client.post(f'/survey/{token}/step/{STEP_PROFILE_GRID}', data={'profile_grid': grid})
    client.post(f'/survey/{token}/step/{STEP_TOPICS}', data={'topics': ['0', '1', '2']})
    client.post(f'/survey/{token}/step/{STEP_SUPPORT_TYPE}', data={'support_type': '0'})
    client.post(f'/survey/{token}/step/{STEP_TARGET_GROUPS}', data={'target_groups': '0'})
    return client.post(f'/survey/{token}/step/{STEP_WHY_REASON}', data={'why_reason': 'Because it matters.'})


# ---------------------------------------------------------------------------
# 1. Happy path — two-value relationship lists render ALL values,
#    comma-separated, not just the first (Communicator: 2 natural_allies,
#    2 friends; distinct from the coder's own Entrepreneur-only coverage).
# ---------------------------------------------------------------------------

def test_communicator_two_value_relationships_render_both_names_on_web_result(client, db):
    token = _start_new(client)
    final = _complete_survey(client, token, {'respondent_type': str(INDIVIDUAL)}, grid='1,0')  # -> communicator
    assert final.status_code == 302

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.persona_id == 'communicator'

    body = client.get(f'/survey/{token}/result').get_data(as_text=True)
    assert 'The Communicator' in body
    assert 'You are the voice!' in body
    # natural_allies: [architect, accountant] -> both must render, comma-separated
    assert 'The Architect, The Accountant' in body
    # friends: [connector, cooperator] -> both must render, comma-separated
    assert 'The Connector, The Cooperator' in body


def test_communicator_two_value_relationships_render_both_names_in_pdf(app):
    """PDF and web share `_persona_card.html`; render `pdf/result.html`
    directly with the real communicator persona dict (WeasyPrint's rasterised
    PDF bytes aren't text-greppable, matching the coder's own PDF-check
    pattern in test_real_survey_e2e.py)."""
    from flask import render_template

    with app.app_context():
        survey = load_survey(REAL_SURVEY_PATH)
    communicator = survey['personas']['communicator']

    with app.app_context():
        html = render_template(
            'pdf/result.html', persona=communicator, personas=survey['personas'],
            fingerprint_svg='<svg></svg>', innovation=None, audience=None,
        )
    assert 'The Architect, The Accountant' in html
    assert 'The Connector, The Cooperator' in html


# ---------------------------------------------------------------------------
# 2. Laggard band tagline — verbatim, including "Wanker", reached through a
#    real low-scoring submission (accountant modifier 0, all three
#    innovation-curve questions left unanswered so they contribute 0).
# ---------------------------------------------------------------------------

def test_laggard_band_tagline_renders_verbatim_on_real_low_score_submission(client, db):
    token = _start_new(client)
    final = _complete_survey(
        client, token, {'respondent_type': str(INDIVIDUAL)},
        motivation=None, ambition=None, space=None, grid='0,0',  # -> accountant, modifier 0
    )
    assert final.status_code == 302

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.innovation_score == 0
    assert submission.innovation_band == 'Laggards'

    body = client.get(f'/survey/{token}/result').get_data(as_text=True)
    assert 'You are a Laggard. Wanker.' in body


def test_laggard_band_tagline_renders_verbatim_in_pdf(app):
    from flask import render_template

    with app.app_context():
        survey = load_survey(REAL_SURVEY_PATH)
    persona = survey['personas']['accountant']
    laggard_band = next(b for b in survey['innovation_curve']['bands'] if b['name'] == 'Laggards')
    innovation = {
        'band': 'Laggards', 'score': 0, 'colour': laggard_band['colour'],
        'tagline': laggard_band['tagline'], 'description': laggard_band['description'],
    }

    with app.app_context():
        html = render_template(
            'pdf/result.html', persona=persona, personas=survey['personas'],
            fingerprint_svg='<svg></svg>', innovation=innovation, audience=None,
        )
    assert 'You are a Laggard. Wanker.' in html


def test_laggard_band_tagline_renders_verbatim_in_both_email_bodies(app):
    from flask import render_template

    with app.app_context():
        survey = load_survey(REAL_SURVEY_PATH)
    persona = survey['personas']['accountant']
    laggard_band = next(b for b in survey['innovation_curve']['bands'] if b['name'] == 'Laggards')
    innovation = {
        'band': 'Laggards', 'score': 0, 'colour': laggard_band['colour'],
        'tagline': laggard_band['tagline'], 'description': laggard_band['description'],
    }

    with app.app_context():
        text_body = render_template(
            'email/result.txt', persona=persona, result_url='https://example.com/r',
            innovation=innovation, audience=None,
        )
        html_body = render_template(
            'email/result.html', persona=persona, result_url='https://example.com/r',
            innovation=innovation, audience=None,
        )
    assert 'You are a Laggard. Wanker.' in text_body
    assert 'You are a Laggard. Wanker.' in html_body


# ---------------------------------------------------------------------------
# 3. audience is None before the router question is ever answered (distinct
#    from the "individual" track, which also resolves to `description` but
#    via an explicit choice) — the un-routed fallback must still work.
# ---------------------------------------------------------------------------

def test_description_falls_back_correctly_when_router_question_is_skipped(client, db):
    """POSTing step 1 with no `respondent_type` value leaves
    `submission.audience` as None for the rest of the flow (the router
    question isn't force-validated like the grid/multi_exact steps are).
    The persona description must still resolve to the individual/default
    wording, not crash, and not show organisation wording."""
    token = _start_new(client)
    final = _complete_survey(client, token, {}, grid='1,1')  # -> entrepreneur, respondent_type skipped
    assert final.status_code == 302

    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.audience is None
    assert submission.persona_id == 'entrepreneur'

    result_response = client.get(f'/survey/{token}/result')
    assert result_response.status_code == 200
    body = result_response.get_data(as_text=True)
    assert 'You see and act upon the opportunities' in body
    assert 'Your organisation sees and acts upon the opportunities' not in body

    pdf_response = client.get(f'/survey/{token}/pdf')
    assert pdf_response.status_code == 200
    assert pdf_response.mimetype == 'application/pdf'


def test_persona_description_macro_falls_back_when_description_organisation_absent(app):
    """Guards the macro itself for a persona that doesn't carry
    `description_organisation` (none of the real 9 currently lack it, but
    the field is optional per the loader/spec) — must not crash, must use
    `description`, even when audience == 'organisation'."""
    from flask import render_template

    persona_without_org_wording = {'name': 'X', 'tagline': 't', 'description': 'Fallback wording.'}
    with app.app_context():
        html = render_template(
            'email/result.txt', persona=persona_without_org_wording,
            result_url='https://example.com/r', innovation=None, audience='organisation',
        )
    assert 'Fallback wording.' in html


# ---------------------------------------------------------------------------
# 4. Regression guard — persona relationships stay OUT of both email bodies
#    (a deliberate, pre-existing gap per the spec, not a new regression).
# ---------------------------------------------------------------------------

def test_email_bodies_never_render_persona_relationships(app):
    from flask import render_template

    with app.app_context():
        survey = load_survey(REAL_SURVEY_PATH)
    entrepreneur = survey['personas']['entrepreneur']  # has 2-value natural_allies + friends

    with app.app_context():
        text_body = render_template(
            'email/result.txt', persona=entrepreneur, result_url='https://example.com/r',
            innovation=None, audience='organisation',
        )
        html_body = render_template(
            'email/result.html', persona=entrepreneur, result_url='https://example.com/r',
            innovation=None, audience='organisation',
        )

    for label in ('Natural allies', 'Friends:', 'Necessities'):
        assert label not in text_body
        assert label not in html_body

    for related_name in ('The Implementer', 'The Cooperator', 'The Communicator', 'The Architect', 'The Accountant'):
        assert related_name not in text_body
        assert related_name not in html_body


# ---------------------------------------------------------------------------
# 5. Failure case — loader must reject innovation-curve bands missing the
#    newly-required `tagline`/`description` fields (backlog #0004). The
#    existing `test_innovation_curve_band_missing_field_raises` parametrize
#    list in test_loader.py only covers name/min/max/colour.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('field_to_drop', ['tagline', 'description'])
def test_innovation_curve_band_missing_tagline_or_description_raises(field_to_drop):
    import yaml

    with open(REAL_SURVEY_PATH) as f:
        data = yaml.safe_load(f)
    del data['innovation_curve']['bands'][0][field_to_drop]

    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as tmp:
        yaml.dump(data, tmp)
        tmp_path = tmp.name

    try:
        with pytest.raises(SurveyConfigError, match=field_to_drop):
            load_survey(tmp_path)
    finally:
        os.remove(tmp_path)


@pytest.mark.parametrize('field_to_blank', ['tagline', 'description'])
def test_innovation_curve_band_empty_string_tagline_or_description_raises(field_to_blank):
    import yaml

    with open(REAL_SURVEY_PATH) as f:
        data = yaml.safe_load(f)
    data['innovation_curve']['bands'][0][field_to_blank] = ''

    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False) as tmp:
        yaml.dump(data, tmp)
        tmp_path = tmp.name

    try:
        with pytest.raises(SurveyConfigError, match=field_to_blank):
            load_survey(tmp_path)
    finally:
        os.remove(tmp_path)
