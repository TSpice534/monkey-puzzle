"""Persona classifier: the interactive profile grid directly resolves a
persona (grid-direct, the primary UI path); weighted scoring is exercised
against the small fixture survey since the real survey.yaml's weighted
questions were replaced by the real 11-question content (backlog #0003);
tie-break/modifiers/negative-weight behaviour is unchanged."""
import os

import pytest

from app.survey.loader import load_survey
from app.survey.persona import (
    PersonaResult, apply_modifiers, classify, classify_submission,
    resolve_profile_persona, score_submission,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_SURVEY_PATH = os.path.join(REPO_ROOT, 'content', 'survey.yaml')
MIN_FIXTURE_PATH = os.path.join(REPO_ROOT, 'tests', 'fixtures', 'survey_min.yaml')

PERSONA_IDS = [
    'documenter', 'implementer', 'developer', 'advocate', 'communicator',
    'activist', 'connector', 'cooperator', 'entrepreneur',
]

# The confirmed profile_grid cell -> persona mapping (content/survey.yaml,
# question `profile_grid`) — see the spec's grid table.
GRID_CELLS = [
    (0, 2, 'developer'),
    (1, 2, 'advocate'),
    (2, 2, 'cooperator'),
    (0, 1, 'implementer'),
    (1, 1, 'entrepreneur'),
    (2, 1, 'connector'),
    (0, 0, 'documenter'),
    (1, 0, 'communicator'),
    (2, 0, 'activist'),
]


@pytest.fixture()
def config():
    """The real survey (content/survey.yaml) — used for grid-direct tests."""
    return load_survey(REAL_SURVEY_PATH)


@pytest.fixture()
def weighted_config():
    """The small fixture survey — no profile grid, exercises the weighted
    scoring engine in isolation (real survey.yaml's weighted questions were
    replaced by the real 11-question content)."""
    return load_survey(MIN_FIXTURE_PATH)


# ---------------------------------------------------------------------------
# Grid-direct persona resolution — the primary UI path (grid is mandatory)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('x, y, expected_persona', GRID_CELLS)
def test_grid_direct_answer_deterministically_yields_persona(config, x, y, expected_persona):
    result = classify_submission({'profile_grid': [x, y]}, config)
    assert result.persona_id == expected_persona
    assert isinstance(result, PersonaResult)
    assert set(result.scores.keys()) == set(PERSONA_IDS)
    assert result.persona['id'] == expected_persona


def test_resolve_profile_persona_returns_the_mapped_persona(config):
    assert resolve_profile_persona({'profile_grid': [1, 1]}, config) == 'entrepreneur'


def test_grid_direct_wins_even_when_weighted_questions_were_answered(config):
    """Only `profile_grid` (type multi_exact/triangle/etc no longer carry
    weights in the real survey) drives the persona — a grid-direct win
    should hold regardless of what else was answered."""
    answers = {
        'profile_grid': [2, 0],       # -> activist
        'motivation': 0,
        'ambition': 1,
        'topics': [0, 1, 2],
    }
    result = classify_submission(answers, config)
    assert result.persona_id == 'activist'


# ---------------------------------------------------------------------------
# Defensive fallback — grid unanswered or malformed (UI-unreachable, since
# the grid is mandatory to advance, but code-covered for direct-DB-edited
# or partial submissions)
# ---------------------------------------------------------------------------

def test_resolve_profile_persona_returns_none_when_grid_unanswered(config):
    assert resolve_profile_persona({}, config) is None


def test_classify_submission_falls_back_to_tie_break_when_grid_unanswered(config):
    result = classify_submission({}, config)
    assert result.persona_id == config['scoring']['tie_break'][0]


@pytest.mark.parametrize('malformed_answer', [None, [1]])
def test_classify_submission_falls_back_to_tie_break_on_malformed_grid_answer(config, malformed_answer):
    result = classify_submission({'profile_grid': malformed_answer}, config)
    assert result.persona_id == config['scoring']['tie_break'][0]


def test_resolve_profile_persona_returns_none_when_survey_has_no_profile_question(weighted_config):
    assert resolve_profile_persona({'q_single': 0}, weighted_config) is None


# ---------------------------------------------------------------------------
# score_submission — weighted scoring engine (exercised via the small
# fixture survey, which still carries weights and no profile grid)
# ---------------------------------------------------------------------------

def test_score_submission_initialises_all_nine_personas_to_zero(weighted_config):
    scores = score_submission({}, weighted_config)
    assert set(scores.keys()) == set(PERSONA_IDS)
    assert all(v == 0.0 for v in scores.values())


def test_score_submission_sums_weights_for_single_answer(weighted_config):
    scores = score_submission({'q_single': 0}, weighted_config)  # "Option A"
    assert scores['developer'] == 2


def test_score_submission_sums_weights_for_multi_answer(weighted_config):
    scores = score_submission({'q_multi': [0, 1]}, weighted_config)
    assert scores['implementer'] == 1
    assert scores['communicator'] == 1


def test_score_submission_ignores_short_text_answers(weighted_config):
    scores = score_submission({'q_short_text': 'Anything else'}, weighted_config)
    assert all(v == 0.0 for v in scores.values())


def test_score_submission_ignores_unknown_question_id(weighted_config):
    scores = score_submission({'not_a_real_question': 0}, weighted_config)
    assert all(v == 0.0 for v in scores.values())


def test_score_submission_ignores_unknown_option_index(weighted_config):
    scores = score_submission({'q_single': 999}, weighted_config)
    assert all(v == 0.0 for v in scores.values())


def test_score_submission_ignores_empty_multi_answer(weighted_config):
    scores = score_submission({'q_multi': []}, weighted_config)
    assert all(v == 0.0 for v in scores.values())


# ---------------------------------------------------------------------------
# apply_modifiers
# ---------------------------------------------------------------------------

def test_apply_modifiers_is_a_noop_when_both_flags_off(weighted_config):
    scores = {pid: float(i) for i, pid in enumerate(PERSONA_IDS)}
    result = apply_modifiers(scores, weighted_config)
    assert result == scores
    assert result is not scores  # returns a copy, not the same object


# ---------------------------------------------------------------------------
# classify — tie-break behaviour
# ---------------------------------------------------------------------------

def test_classify_all_zero_vector_uses_tie_break_first(weighted_config):
    scores = {pid: 0.0 for pid in PERSONA_IDS}
    result = classify(scores, weighted_config)
    assert result.persona_id == weighted_config['scoring']['tie_break'][0]


def test_classify_breaks_ties_by_tie_break_order(weighted_config):
    tie_break = weighted_config['scoring']['tie_break']
    # Give the top two tie_break entries an equal, highest score.
    scores = {pid: 0.0 for pid in PERSONA_IDS}
    scores[tie_break[0]] = 5.0
    scores[tie_break[1]] = 5.0
    result = classify(scores, weighted_config)
    assert result.persona_id == tie_break[0]


def test_classify_tie_break_is_deterministic_across_calls(weighted_config):
    scores = {pid: 0.0 for pid in PERSONA_IDS}
    scores[PERSONA_IDS[3]] = 1.0
    scores[PERSONA_IDS[5]] = 1.0
    results = {classify(scores, weighted_config).persona_id for _ in range(5)}
    assert len(results) == 1


def test_classify_returns_full_nine_dim_vector(weighted_config):
    scores = {pid: 0.0 for pid in PERSONA_IDS}
    scores['developer'] = 3.0
    result = classify(scores, weighted_config)
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
