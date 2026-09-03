"""Independent tester verification for backlog #0002 (Rogers' innovation-curve
scoring + Documenter->Accountant rename), against the REAL content/survey.yaml.

This module exists specifically to independently re-verify the risk areas the
coder's own changes.md flagged for manual verification, going beyond "the
route returns 200" / "the template string contains X":

  - the innovation card's exact position in the rendered result.html HTML
    (directly below the grid card, before the share/save card);
  - the two unlabelled `motivation` spectrum box-row stops: rendered blank
    AND still selectable AND contributing the correct score to the total;
  - WeasyPrint's actual PDF *bytes* (decompressed content stream) contain the
    band colour as a real fill operator, not just that the HTML fed to
    WeasyPrint mentions the colour string;
  - the actual email message dispatched through the real route (captured via
    Flask-Mail's `record_messages()`, not a direct template render) has the
    band name in both the HTML and plain-text bodies;
  - a defensive failure path: a malformed answer never raises and contributes
    zero to the innovation score.
"""
import os
import re
import zlib

import pytest

from app import mail
from app.models import Submission
from app.survey.loader import clear_survey_cache
from app.survey.persona import resolve_innovation_curve

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_SURVEY_PATH = os.path.join(REPO_ROOT, 'content', 'survey.yaml')

INDIVIDUAL = 0

STEP_RESPONDENT_TYPE = 1
STEP_MOTIVATION = 2
STEP_AMBITION = 3
STEP_SPACE_TO_PROGRESS = 4
STEP_NEED_MOST = 5
STEP_HAVE_ENOUGH = 6
STEP_PROFILE = 7
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


def _complete_survey(client, motivation='0', ambition='0', space_to_progress='0', approach='1', scope='1'):
    """Walk all 12 real-survey steps to completion. approach='1', scope='1'
    -> entrepreneur (persona modifier +2)."""
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
    client.post(f'/survey/{token}/step/{STEP_MOTIVATION}', data={'motivation': motivation})
    client.post(f'/survey/{token}/step/{STEP_AMBITION}', data={'ambition': ambition})
    client.post(f'/survey/{token}/step/{STEP_SPACE_TO_PROGRESS}', data={'space_to_progress': space_to_progress})
    client.post(f'/survey/{token}/step/{STEP_NEED_MOST}', data={'need_most': '0'})
    client.post(f'/survey/{token}/step/{STEP_HAVE_ENOUGH}', data={'have_enough': '0'})
    client.post(f'/survey/{token}/step/{STEP_PROFILE}', data={'profile_approach': approach, 'profile_scope': scope})
    client.post(f'/survey/{token}/step/{STEP_TOPICS}', data={'topics': ['0', '1', '2']})
    client.post(f'/survey/{token}/step/{STEP_SUPPORT_TYPE}', data={'support_type': '0'})
    client.post(f'/survey/{token}/step/{STEP_TARGET_GROUPS}', data={'target_groups': '0'})
    client.post(f'/survey/{token}/step/{STEP_WHY_REASON}', data={'why_reason': 'Because it matters.'})
    return token


def _hex_to_rg_operator(hex_colour):
    """Convert a CSS hex colour to the PDF content-stream 'rg' fill-colour
    operator WeasyPrint would emit for it (6-decimal fractions, as observed
    in actual generated output)."""
    hex_colour = hex_colour.lstrip('#')
    r = int(hex_colour[0:2], 16) / 255
    g = int(hex_colour[2:4], 16) / 255
    b = int(hex_colour[4:6], 16) / 255
    return f'{r:.6f} {g:.6f} {b:.6f} rg'.encode()


def _decompressed_pdf_streams(pdf_bytes):
    streams = re.findall(rb'stream\r?\n(.*?)endstream', pdf_bytes, re.S)
    out = []
    for s in streams:
        try:
            out.append(zlib.decompress(s))
        except zlib.error:
            out.append(s)
    return out


# ---------------------------------------------------------------------------
# Happy path — full flow, band card position on the real web result page
# ---------------------------------------------------------------------------

def test_happy_path_innovation_band_persisted_and_card_positioned_between_grid_and_share(client, db):
    token = _complete_survey(client)  # motivation=0,ambition=0,space=0 (sum 3) + entrepreneur (+2) = 5
    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.innovation_score == 5
    assert submission.innovation_band == 'Late Majority'

    body = client.get(f'/survey/{token}/result').get_data(as_text=True)
    assert 'Your focus group on the innovation curve' in body
    assert 'Late Majority' in body

    grid_pos = body.index('Your position on the grid')
    innovation_pos = body.index('Your focus group on the innovation curve')
    share_pos = body.index('Share or save your result')
    assert grid_pos < innovation_pos < share_pos, (
        'innovation card must render strictly between the grid card and the share card'
    )


# ---------------------------------------------------------------------------
# Edge case — the two unlabelled `motivation` spectrum box-row stops: blank
# in the rendered HTML, still selectable, and contribute their real score.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('index, expected_contribution', [(1, 2), (3, 4)])
def test_motivation_unlabelled_stop_renders_blank_but_scores_correctly(client, db, index, expected_contribution):
    # Confirm the step renders with no visible placeholder text for either
    # unlabelled stop before submitting.
    token = _start_new(client)
    client.post(f'/survey/{token}/step/{STEP_RESPONDENT_TYPE}', data={'respondent_type': str(INDIVIDUAL)})
    body = client.get(f'/survey/{token}/step/{STEP_MOTIVATION}').get_data(as_text=True)
    assert 'Intermediate position' not in body

    # Submit the unlabelled stop as the actual answer and drive to completion
    # with ambition/space_to_progress pinned to their lowest (score 1) option,
    # so the total is directly attributable to the unlabelled motivation score.
    token = _complete_survey(client, motivation=str(index), ambition='0', space_to_progress='0', approach='0', scope='0')
    # profile pair (approach=0, scope=0) -> accountant, modifier +0 (content/survey.yaml)
    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.innovation_score == expected_contribution + 1 + 1 + 0


# ---------------------------------------------------------------------------
# WeasyPrint PDF — actual rendered bytes contain the band colour as a real
# fill operator (not just that the source HTML string mentions the hex).
# ---------------------------------------------------------------------------

def test_pdf_bytes_actually_contain_the_band_colour_fill_operator(client, db):
    token = _complete_survey(client)  # -> Late Majority, colour #e67e22
    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.innovation_band == 'Late Majority'

    response = client.get(f'/survey/{token}/pdf')
    assert response.status_code == 200
    assert response.data.startswith(b'%PDF')

    expected_operator = _hex_to_rg_operator('#e67e22')
    combined = b'\n'.join(_decompressed_pdf_streams(response.data))
    assert expected_operator in combined, (
        "expected the band's colour to appear as a real PDF fill-colour operator "
        f"({expected_operator!r}) in the decompressed content stream, not just in "
        "the source HTML handed to WeasyPrint"
    )


# ---------------------------------------------------------------------------
# Email — actual dispatched message (via Flask-Mail's record_messages, real
# route, real background thread), not a direct template render.
# ---------------------------------------------------------------------------

def test_email_route_actual_dispatched_message_contains_band_name_in_both_bodies(client, app, db):
    app.config['MAIL_SERVER'] = 'smtp.example.invalid'
    app.config['MAIL_DEFAULT_SENDER'] = 'noreply@example.com'

    # High-scoring path -> Innovators (inventor profile pair, +4 modifier).
    token = _complete_survey(client, motivation='4', ambition='2', space_to_progress='2', approach='2', scope='0')
    submission = db.session.query(Submission).filter_by(token=token).one()
    assert submission.innovation_band == 'Innovators'

    with mail.record_messages() as outbox:
        response = client.post(f'/survey/{token}/email', data={'email': 'someone@example.com'})
        assert response.status_code == 302

        # The route fires a daemon background thread — give it a bounded
        # window to finish rather than asserting on internals.
        import time
        deadline = time.time() + 5
        while not outbox and time.time() < deadline:
            time.sleep(0.05)

    assert len(outbox) == 1
    msg = outbox[0]
    assert 'Innovators' in msg.html
    assert 'Innovators' in msg.body


# ---------------------------------------------------------------------------
# Failure case — malformed answers must not raise, and must contribute zero.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('malformed_answer', [
    'not-an-int',
    [0, 1],
    3.5,
    None,
    True,   # bool is an int subclass — must NOT be treated as a valid index
])
def test_resolve_innovation_curve_malformed_answer_never_raises_and_contributes_zero(malformed_answer):
    from app.survey.loader import load_survey
    config = load_survey(REAL_SURVEY_PATH)

    answers = {
        'motivation': malformed_answer,
        'ambition': 0,          # score 1
        'space_to_progress': 0,  # score 1
    }
    result = resolve_innovation_curve(answers, config, 'accountant')  # +0 modifier
    assert result is not None
    assert result.score == 2  # motivation contributed 0, not a crash
