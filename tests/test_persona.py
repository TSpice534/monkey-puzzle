"""Persona classifier: crafted answer sets deterministically yield each of
the nine personas; tie-break is stable; modifiers are MVP no-ops; an
all-zero vector still classifies (via tie_break[0])."""
import os

import pytest

from app.survey.loader import load_survey
from app.survey.persona import (
    PersonaResult, apply_modifiers, classify, classify_submission, score_submission,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_SURVEY_PATH = os.path.join(REPO_ROOT, 'content', 'survey.yaml')

PERSONA_IDS = [
    'documenter', 'implementer', 'developer', 'advocate', 'communicator',
    'activist', 'connector', 'cooperator', 'entrepreneur',
]


@pytest.fixture()
def config():
    return load_survey(REAL_SURVEY_PATH)


# ---------------------------------------------------------------------------
# Every persona is reachable via the placeholder content
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('index, expected_persona', list(enumerate(PERSONA_IDS)))
def test_role_preference_answer_deterministically_yields_persona(config, index, expected_persona):
    """`role_preference` is the placeholder survey's single dominant question —
    one option per persona, weighted well above anything else — so answering
    it alone must drive the classifier straight to that persona."""
    result = classify_submission({'role_preference': index}, config)
    assert result.persona_id == expected_persona
    assert isinstance(result, PersonaResult)
    assert set(result.scores.keys()) == set(PERSONA_IDS)
    assert result.persona['id'] == expected_persona


# ---------------------------------------------------------------------------
# score_submission
# ---------------------------------------------------------------------------

def test_score_submission_initialises_all_nine_personas_to_zero(config):
    scores = score_submission({}, config)
    assert set(scores.keys()) == set(PERSONA_IDS)
    assert all(v == 0.0 for v in scores.values())


def test_score_submission_sums_weights_for_single_answer(config):
    scores = score_submission({'mission_clarity': 0}, config)  # "Crystal clear"
    assert scores['developer'] == 2
    assert scores['implementer'] == 1


def test_score_submission_sums_weights_for_multi_answer(config):
    scores = score_submission({'change_role': [1, 2]}, config)
    assert scores['activist'] == 2
    assert scores['connector'] == 2


def test_score_submission_ignores_short_text_answers(config):
    scores = score_submission({'comms_barrier': 'People just don\'t read reports'}, config)
    assert all(v == 0.0 for v in scores.values())


def test_score_submission_ignores_unknown_question_id(config):
    scores = score_submission({'not_a_real_question': 0}, config)
    assert all(v == 0.0 for v in scores.values())


def test_score_submission_ignores_unknown_option_index(config):
    scores = score_submission({'mission_clarity': 999}, config)
    assert all(v == 0.0 for v in scores.values())


def test_score_submission_ignores_empty_multi_answer(config):
    scores = score_submission({'change_role': []}, config)
    assert all(v == 0.0 for v in scores.values())


# ---------------------------------------------------------------------------
# apply_modifiers
# ---------------------------------------------------------------------------

def test_apply_modifiers_is_a_noop_when_both_flags_off(config):
    scores = {pid: float(i) for i, pid in enumerate(PERSONA_IDS)}
    result = apply_modifiers(scores, config)
    assert result == scores
    assert result is not scores  # returns a copy, not the same object


# ---------------------------------------------------------------------------
# classify — tie-break behaviour
# ---------------------------------------------------------------------------

def test_classify_all_zero_vector_uses_tie_break_first(config):
    scores = {pid: 0.0 for pid in PERSONA_IDS}
    result = classify(scores, config)
    assert result.persona_id == config['scoring']['tie_break'][0]


def test_classify_breaks_ties_by_tie_break_order(config):
    tie_break = config['scoring']['tie_break']
    # Give the top two tie_break entries an equal, highest score.
    scores = {pid: 0.0 for pid in PERSONA_IDS}
    scores[tie_break[0]] = 5.0
    scores[tie_break[1]] = 5.0
    result = classify(scores, config)
    assert result.persona_id == tie_break[0]


def test_classify_tie_break_is_deterministic_across_calls(config):
    scores = {pid: 0.0 for pid in PERSONA_IDS}
    scores[PERSONA_IDS[3]] = 1.0
    scores[PERSONA_IDS[5]] = 1.0
    results = {classify(scores, config).persona_id for _ in range(5)}
    assert len(results) == 1


def test_classify_returns_full_nine_dim_vector(config):
    scores = {pid: 0.0 for pid in PERSONA_IDS}
    scores['developer'] = 3.0
    result = classify(scores, config)
    assert set(result.scores.keys()) == set(PERSONA_IDS)


# ---------------------------------------------------------------------------
# Negative weights — spec requires mirroring Donut's negative-weight support
# ---------------------------------------------------------------------------

def _negative_weight_config():
    """A minimal config (no loader round-trip needed) with one option that
    carries a negative weight, to exercise score_submission/classify's
    negative-weight support directly."""
    personas = {pid: {'id': pid, 'name': pid} for pid in PERSONA_IDS}
    return {
        'personas': personas,
        'questions': [
            {
                'id': 'q1',
                'type': 'single',
                'options': [
                    {
                        'index': 0,
                        'label': 'Boosts developer, penalises documenter',
                        'weights': {'developer': 2, 'documenter': -3},
                    },
                    {
                        'index': 1,
                        'label': 'Neutral',
                        'weights': {'documenter': 1},
                    },
                ],
            },
        ],
        'scoring': {
            'method': 'persona_vector',
            'tie_break': list(PERSONA_IDS),
            'equity_modifier': {'enabled': False},
            'rogers_curve': {'enabled': False},
        },
    }


def test_score_submission_applies_negative_weights():
    config = _negative_weight_config()
    scores = score_submission({'q1': 0}, config)
    assert scores['developer'] == 2
    assert scores['documenter'] == -3


def test_classify_lets_a_negative_weight_change_the_winner():
    """documenter starts ahead from an earlier (hypothetical) answer, but a
    negative weight on this question should be able to pull it below
    developer and flip the winner."""
    config = _negative_weight_config()
    result = classify_submission({'q1': 0}, config)
    assert result.persona_id == 'developer'
    assert result.scores['documenter'] == -3
