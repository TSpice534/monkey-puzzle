"""Persona classifier: the interactive profile grid directly resolves a
persona (grid-direct, the primary UI path); weighted scoring is exercised
against the small fixture survey since the real survey.yaml's weighted
questions were replaced by the real 11-question content (backlog #0003);
tie-break/modifiers/negative-weight behaviour is unchanged."""
import os

import pytest

from app.survey.loader import load_survey
from app.survey.persona import (
    InnovationCurveResult, PersonaResult, _join_phrases, _statement_phrase, apply_modifiers, classify,
    classify_submission, resolve_innovation_curve, resolve_now_next, resolve_profile_persona,
    score_submission,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_SURVEY_PATH = os.path.join(REPO_ROOT, 'content', 'survey.yaml')
MIN_FIXTURE_PATH = os.path.join(REPO_ROOT, 'tests', 'fixtures', 'survey_min.yaml')

PERSONA_IDS = [
    'accountant', 'implementer', 'developer', 'advocate', 'communicator',
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
    (0, 0, 'accountant'),
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
                        'label': 'Boosts developer, penalises accountant',
                        'weights': {'developer': 2, 'accountant': -3},
                    },
                    {
                        'index': 1,
                        'label': 'Neutral',
                        'weights': {'accountant': 1},
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
    assert scores['accountant'] == -3


def test_classify_lets_a_negative_weight_change_the_winner():
    """accountant starts ahead from an earlier (hypothetical) answer, but a
    negative weight on this question should be able to pull it below
    developer and flip the winner."""
    config = _negative_weight_config()
    result = classify_submission({'q1': 0}, config)
    assert result.persona_id == 'developer'
    assert result.scores['accountant'] == -3


# ---------------------------------------------------------------------------
# resolve_innovation_curve — Rogers' innovation-curve aggregation (backlog
# #0002), exercised against the real config so worked examples cross-check
# the real content/survey.yaml scores/modifiers/bands.
# ---------------------------------------------------------------------------

def test_resolve_innovation_curve_low_scores_and_entrepreneur_modifier_gives_late_majority(config):
    # motivation=0 (1), ambition=0 (1), space_to_progress=0 (1) -> sum 3;
    # entrepreneur modifier +2 -> total 5 -> Late Majority (3-7).
    answers = {'motivation': 0, 'ambition': 0, 'space_to_progress': 0}
    result = resolve_innovation_curve(answers, config, 'entrepreneur')
    assert isinstance(result, InnovationCurveResult)
    assert result.score == 5
    assert result.band == 'Late Majority'


def test_resolve_innovation_curve_high_scores_and_developer_modifier_gives_innovators(config):
    # motivation=4 (5), ambition=2 (5), space_to_progress=2 (5) -> sum 15;
    # developer modifier +4 -> total 19 -> Innovators (15-20).
    answers = {'motivation': 4, 'ambition': 2, 'space_to_progress': 2}
    result = resolve_innovation_curve(answers, config, 'developer')
    assert result.score == 19
    assert result.band == 'Innovators'


def test_resolve_innovation_curve_accountant_gives_a_zero_modifier(config):
    answers = {'motivation': 0, 'ambition': 0, 'space_to_progress': 0}
    result = resolve_innovation_curve(answers, config, 'accountant')
    assert result.score == 3  # no modifier added


def test_resolve_innovation_curve_returns_none_when_survey_has_no_innovation_curve(weighted_config):
    assert resolve_innovation_curve({}, weighted_config, 'developer') is None


def test_resolve_innovation_curve_missing_answers_contribute_zero(config):
    result = resolve_innovation_curve({}, config, 'accountant')
    assert result.score == 0
    assert result.band == 'Laggards'


def test_resolve_innovation_curve_unknown_persona_id_contributes_zero_modifier(config):
    answers = {'motivation': 0, 'ambition': 0, 'space_to_progress': 0}
    result = resolve_innovation_curve(answers, config, 'not-a-real-persona')
    assert result.score == 3


# ---------------------------------------------------------------------------
# _join_phrases — Oxford-comma joining helper
# ---------------------------------------------------------------------------

def test_join_phrases_empty_list():
    assert _join_phrases([]) == ''


def test_join_phrases_one_item():
    assert _join_phrases(['Water']) == 'Water'


def test_join_phrases_two_items_no_oxford_comma():
    assert _join_phrases(['Water', 'Energy']) == 'Water and Energy'


def test_join_phrases_three_items_oxford_comma():
    assert _join_phrases(['Water', 'Energy', 'Food']) == 'Water, Energy, and Food'


# ---------------------------------------------------------------------------
# _statement_phrase — statement_phrase_organisation > statement_phrase > label
# ---------------------------------------------------------------------------

def test_statement_phrase_falls_back_to_label_when_absent():
    option = {'label': 'Water'}
    assert _statement_phrase(option, None) == 'Water'
    assert _statement_phrase(option, 'organisation') == 'Water'


def test_statement_phrase_used_when_present():
    option = {'label': 'Capacity', 'statement_phrase': 'capacity'}
    assert _statement_phrase(option, None) == 'capacity'


def test_statement_phrase_organisation_only_wins_on_org_track():
    option = {
        'label': 'Capacity', 'statement_phrase': 'capacity',
        'statement_phrase_organisation': 'organisational capacity',
    }
    assert _statement_phrase(option, 'organisation') == 'organisational capacity'
    assert _statement_phrase(option, 'individual') == 'capacity'
    assert _statement_phrase(option, None) == 'capacity'


def test_statement_phrase_organisation_absent_falls_back_to_statement_phrase():
    """OPEN QUESTION 1 (backlog #0007): no org-register copy has been
    supplied for the real survey — confirm the fallback chain still resolves
    to the individual-register statement_phrase on the org track."""
    option = {'label': 'Capacity', 'statement_phrase': 'capacity'}
    assert _statement_phrase(option, 'organisation') == 'capacity'


# ---------------------------------------------------------------------------
# resolve_now_next — Now/Next narrative statement assembly (backlog #0007),
# exercised against the real config so worked examples cross-check the real
# content/survey.yaml copy and per-option statement_phrase values.
# ---------------------------------------------------------------------------

def test_resolve_now_next_returns_none_when_survey_has_no_now_next(weighted_config):
    assert resolve_now_next({}, weighted_config, None) is None


def test_resolve_now_next_now_sentence_joins_edge_pick_phrases(config):
    """backlog #0010: an edge pick on `have_enough` ([0, 1]) resolves to both
    flanking corners' statement_phrases joined with 'and', not a single
    phrase."""
    answers = {
        'topics': [0, 1, 2],
        'have_enough': [0, 1],     # Capacity & Knowledge edge -> 'capacity and knowledge'
    }
    result = resolve_now_next(answers, config, None)
    assert 'capacity and knowledge' in result['now']


def test_resolve_now_next_next_sentence_joins_edge_pick_phrases(config):
    answers = {
        'need_most': [0, 1],       # More capacity & More knowledge edge -> 'capacity and knowledge'
        'support_type': 0,
        'target_groups': 0,
    }
    result = resolve_now_next(answers, config, None)
    assert 'more capacity and knowledge' in result['next']


def test_resolve_now_next_next_sentence_joins_support_type_edge_pick_phrases(config):
    """backlog #0010: `support_type` is the third affected triangle question
    (the coder's own tests only covered `need_most` and `have_enough`) — an
    edge pick on it must join the same way, in context in the full 'next'
    sentence."""
    answers = {
        'need_most': 0,             # More capacity -> 'capacity'
        'support_type': [0, 1],     # Information & Training edge -> 'information and training'
        'target_groups': 0,
    }
    result = resolve_now_next(answers, config, None)
    assert (
        'This could be achieved by accessing more information and training '
        'to address this challenge.' in result['next']
    )


def test_resolve_now_next_now_sentence_skips_a_single_out_of_range_edge_index(config):
    """Spec's defensive edge case: a malformed/out-of-range edge index
    (e.g. [0, 9]) must not crash `resolve_now_next` — `options_by_index.get`
    returns None for the bad index and it is silently skipped, leaving just
    the one valid phrase (not joined with 'and')."""
    answers = {
        'topics': [0, 1, 2],
        'have_enough': [0, 9],      # 9 doesn't exist on a 3-option triangle
    }
    result = resolve_now_next(answers, config, None)
    assert result['now'] is not None
    assert 'capacity' in result['now']
    assert 'capacity and' not in result['now']


def test_resolve_now_next_now_is_none_when_edge_pick_is_entirely_out_of_range(config):
    """Both indices of an edge pick are out of range -> no phrases resolve
    at all -> the source question is treated as if unanswered (existing
    defensive `continue`), not a crash or an empty-string phrase."""
    answers = {
        'topics': [0, 1, 2],
        'have_enough': [8, 9],
    }
    result = resolve_now_next(answers, config, None)
    assert result['now'] is None


def test_resolve_now_next_now_sentence_joins_three_topics_and_have_enough_phrase(config):
    answers = {
        'topics': [0, 1, 2],       # Water, Food & Drinks, Energy
        'have_enough': 0,          # Capacity -> statement_phrase 'capacity'
    }
    result = resolve_now_next(answers, config, None)
    assert result['now'] == (
        'Your current sustainability focus is Water, Food & Drinks, and Energy, '
        'where you feel you have a good amount of capacity to help achieve your goals.'
    )


def test_resolve_now_next_next_sentence_joins_three_phrases(config):
    answers = {
        'need_most': 0,        # More capacity -> 'capacity'
        'support_type': 0,     # Information -> 'information'
        'target_groups': 0,    # I want to engage my audience -> 'with your audience'
    }
    result = resolve_now_next(answers, config, None)
    assert result['next'] == (
        'In order to progress your ambitions, you are looking for more capacity. '
        'This could be achieved by accessing more information to address this '
        'challenge. In terms of collaboration ambitions, you are keen to engage more '
        'with your audience.'
    )


def test_resolve_now_next_now_is_none_when_topics_missing(config):
    answers = {'have_enough': 0}
    result = resolve_now_next(answers, config, None)
    assert result['now'] is None


def test_resolve_now_next_now_is_none_when_have_enough_missing(config):
    answers = {'topics': [0, 1, 2]}
    result = resolve_now_next(answers, config, None)
    assert result['now'] is None


def test_resolve_now_next_next_is_none_when_a_required_answer_is_missing(config):
    answers = {'need_most': 0, 'support_type': 0}  # target_groups missing
    result = resolve_now_next(answers, config, None)
    assert result['next'] is None


def test_resolve_now_next_both_none_when_no_source_answers(config):
    result = resolve_now_next({}, config, None)
    assert result == {'now': None, 'next': None}


def test_resolve_now_next_organisation_falls_back_to_individual_copy(config):
    """No org-register now_next copy is supplied (OPEN QUESTION 1) — the
    organisation track must render the same statements as the individual
    track via the fallback chain, not blank out."""
    answers = {
        'topics': [0, 1, 2], 'have_enough': 0,
        'need_most': 0, 'support_type': 0, 'target_groups': 0,
    }
    individual = resolve_now_next(answers, config, 'individual')
    organisation = resolve_now_next(answers, config, 'organisation')
    assert individual == organisation
    assert organisation['now'] is not None
    assert organisation['next'] is not None
