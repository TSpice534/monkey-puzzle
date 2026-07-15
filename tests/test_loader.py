"""content/survey.yaml loader: schema validation, normalisation, and the
data-driven contract (editing a weight changes scoring without engine
changes)."""
import copy
import os

import pytest
import yaml

from app.survey.loader import SurveyConfigError, load_survey

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_SURVEY_PATH = os.path.join(REPO_ROOT, 'content', 'survey.yaml')

PERSONA_IDS = [
    'accountant', 'implementer', 'developer', 'advocate', 'communicator',
    'activist', 'connector', 'cooperator', 'entrepreneur',
]


def _base_config():
    """A minimal-but-valid config dict, mirroring tests/fixtures/survey_min.yaml,
    used as a starting point for malformed-YAML mutation tests."""
    personas = {
        pid: {'name': f'The {pid.title()}', 'tagline': 'Tagline', 'description': 'Description'}
        for pid in PERSONA_IDS
    }
    return {
        'meta': {'version': 1, 'title': 'Fixture Survey', 'personas_count': 9},
        'personas': personas,
        'questions': [
            {
                'id': 'q_single',
                'type': 'single',
                'prompt': 'Pick one',
                'dimension': 'roots',
                'options': [
                    {'label': 'Option A', 'weights': {'developer': 2}},
                    {'label': 'Option B', 'weights': {'accountant': 2}},
                ],
            },
            {
                'id': 'q_short_text',
                'type': 'short_text',
                'prompt': 'Anything else?',
                'dimension': 'communication_needs',
            },
        ],
        'scoring': {
            'method': 'persona_vector',
            'tie_break': list(PERSONA_IDS),
            'equity_modifier': {'enabled': False},
            'rogers_curve': {'enabled': False},
        },
    }


def _write_yaml(tmp_path, data, name='survey.yaml'):
    path = tmp_path / name
    path.write_text(yaml.safe_dump(data), encoding='utf-8')
    return str(path)


# ---------------------------------------------------------------------------
# Valid content
# ---------------------------------------------------------------------------

def test_real_placeholder_survey_loads_without_error():
    config = load_survey(REAL_SURVEY_PATH)
    assert set(config['personas'].keys()) == set(PERSONA_IDS)
    # 10-15 scored questions plus the respondent-type router question.
    assert 11 <= len(config['questions']) <= 20


def test_real_placeholder_survey_has_a_respondent_type_router():
    config = load_survey(REAL_SURVEY_PATH)
    router_id = config['respondent_type_question']
    assert config['questions'][0]['id'] == router_id
    router = config['questions'][0]
    values = {opt['audience_value'] for opt in router['options']}
    assert values == {'individual', 'organisation'}


def test_real_placeholder_survey_individual_and_organisation_tracks_are_balanced():
    """Not a hard product requirement, just a sanity check that placeholder
    content gives both tracks comparable depth — catches an obviously
    lopsided edit (e.g. one branch question forgotten) without pinning an
    exact count either track has to hit."""
    from app.survey.loader import effective_questions

    config = load_survey(REAL_SURVEY_PATH)
    individual_total = len(effective_questions(config, 'individual'))
    organisation_total = len(effective_questions(config, 'organisation'))
    assert individual_total == organisation_total


def test_valid_config_normalises_persona_ids(tmp_path):
    path = _write_yaml(tmp_path, _base_config())
    config = load_survey(path)
    for pid, persona in config['personas'].items():
        assert persona['id'] == pid


def test_valid_config_attaches_option_indices(tmp_path):
    path = _write_yaml(tmp_path, _base_config())
    config = load_survey(path)
    single_q = next(q for q in config['questions'] if q['id'] == 'q_single')
    assert [opt['index'] for opt in single_q['options']] == [0, 1]


def test_short_text_question_has_no_options(tmp_path):
    path = _write_yaml(tmp_path, _base_config())
    config = load_survey(path)
    text_q = next(q for q in config['questions'] if q['id'] == 'q_short_text')
    assert 'options' not in text_q or not text_q['options']


def test_persona_relation_defaults_are_empty_lists(tmp_path):
    path = _write_yaml(tmp_path, _base_config())
    config = load_survey(path)
    accountant = config['personas']['accountant']
    assert accountant['natural_allies'] == []
    assert accountant['friends'] == []
    assert accountant['necessity'] == []
    assert accountant['case_studies'] == []
    assert accountant['resources'] == []


def test_negative_option_weight_is_valid(tmp_path):
    """The spec mirrors Donut's negative-weight support — a negative weight
    must load cleanly, not be rejected as 'non-numeric'."""
    data = _base_config()
    data['questions'][0]['options'][0]['weights'] = {'developer': -2}
    config = load_survey(_write_yaml(tmp_path, data))
    single_q = next(q for q in config['questions'] if q['id'] == 'q_single')
    assert single_q['options'][0]['weights']['developer'] == -2


def test_editing_a_weight_changes_scoring_result(tmp_path):
    """The data-driven contract: change a weight in the YAML, re-run the same
    answers, and the winning persona should change — no engine change needed."""
    from app.survey.persona import classify_submission

    config = load_survey(_write_yaml(tmp_path, _base_config()))
    answers = {'q_single': 0}  # picks "Option A" -> developer: 2
    result = classify_submission(answers, config)
    assert result.persona_id == 'developer'

    mutated = _base_config()
    mutated['questions'][0]['options'][0]['weights'] = {'accountant': 5}
    config2 = load_survey(_write_yaml(tmp_path, mutated, name='survey2.yaml'))
    result2 = classify_submission(answers, config2)
    assert result2.persona_id == 'accountant'


# ---------------------------------------------------------------------------
# Malformed YAML -> SurveyConfigError
# ---------------------------------------------------------------------------

def test_missing_yaml_file_raises_survey_config_error(tmp_path):
    with pytest.raises(SurveyConfigError):
        load_survey(str(tmp_path / 'does-not-exist.yaml'))


def test_non_mapping_yaml_raises_survey_config_error(tmp_path):
    path = tmp_path / 'survey.yaml'
    path.write_text('- just\n- a\n- list\n', encoding='utf-8')
    with pytest.raises(SurveyConfigError):
        load_survey(str(path))


def test_missing_top_level_key_raises(tmp_path):
    data = _base_config()
    del data['scoring']
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_wrong_persona_count_raises(tmp_path):
    data = _base_config()
    del data['personas']['entrepreneur']
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_persona_missing_required_field_raises(tmp_path):
    data = _base_config()
    del data['personas']['accountant']['tagline']
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_persona_bad_natural_allies_reference_raises(tmp_path):
    data = _base_config()
    data['personas']['accountant']['natural_allies'] = ['not-a-real-persona']
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_persona_non_string_description_organisation_raises(tmp_path):
    data = _base_config()
    data['personas']['accountant']['description_organisation'] = 123
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_persona_empty_description_organisation_raises(tmp_path):
    data = _base_config()
    data['personas']['accountant']['description_organisation'] = ''
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_persona_absent_description_organisation_is_valid(tmp_path):
    path = _write_yaml(tmp_path, _base_config())
    config = load_survey(path)
    assert 'description_organisation' not in config['personas']['accountant']


def test_persona_valid_description_organisation_loads(tmp_path):
    data = _base_config()
    data['personas']['accountant']['description_organisation'] = 'Your organisation wording'
    config = load_survey(_write_yaml(tmp_path, data))
    assert config['personas']['accountant']['description_organisation'] == 'Your organisation wording'


def test_persona_case_study_missing_url_raises(tmp_path):
    data = _base_config()
    data['personas']['accountant']['case_studies'] = [{'title': 'No URL'}]
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_duplicate_question_id_raises(tmp_path):
    data = _base_config()
    data['questions'].append(copy.deepcopy(data['questions'][0]))
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_invalid_question_type_raises(tmp_path):
    data = _base_config()
    data['questions'][0]['type'] = 'not-a-real-type'
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_scored_question_with_one_option_raises(tmp_path):
    data = _base_config()
    data['questions'][0]['options'] = [{'label': 'Only one', 'weights': {'accountant': 1}}]
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_option_weight_referencing_unknown_persona_raises(tmp_path):
    data = _base_config()
    data['questions'][0]['options'][0]['weights'] = {'not-a-real-persona': 1}
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_option_weight_non_numeric_raises(tmp_path):
    data = _base_config()
    data['questions'][0]['options'][0]['weights'] = {'accountant': 'a lot'}
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_boolean_weight_raises(tmp_path):
    """bool is a subclass of int in Python — guard against `weights: {x: true}`
    silently passing the numeric check."""
    data = _base_config()
    data['questions'][0]['options'][0]['weights'] = {'accountant': True}
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_short_text_with_options_raises(tmp_path):
    data = _base_config()
    data['questions'][1]['options'] = [{'label': 'Should not be here', 'weights': {'accountant': 1}}]
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_wrong_scoring_method_raises(tmp_path):
    data = _base_config()
    data['scoring']['method'] = 'something_else'
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_tie_break_not_a_permutation_raises(tmp_path):
    data = _base_config()
    data['scoring']['tie_break'] = PERSONA_IDS[:-1]  # missing one id
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_tie_break_with_duplicate_raises(tmp_path):
    data = _base_config()
    data['scoring']['tie_break'] = PERSONA_IDS[:-1] + [PERSONA_IDS[0]]
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_scoring_hook_missing_enabled_key_raises(tmp_path):
    data = _base_config()
    data['scoring']['equity_modifier'] = {}
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


# ---------------------------------------------------------------------------
# Respondent-type router question + audience tagging
# ---------------------------------------------------------------------------

def _router_question():
    return {
        'id': 'respondent_type',
        'type': 'single',
        'prompt': 'Individual or organisation?',
        'options': [
            {'label': 'As an individual', 'audience_value': 'individual'},
            {'label': 'On behalf of an organisation', 'audience_value': 'organisation'},
        ],
    }


def _config_with_router():
    data = _base_config()
    data['respondent_type_question'] = 'respondent_type'
    data['questions'].insert(0, _router_question())
    return data


def test_router_question_loads_and_normalises_option_indices(tmp_path):
    config = load_survey(_write_yaml(tmp_path, _config_with_router()))
    router = config['questions'][0]
    assert router['id'] == config['respondent_type_question']
    assert [opt['index'] for opt in router['options']] == [0, 1]


def test_router_question_must_be_first(tmp_path):
    data = _config_with_router()
    # Move the router question to the end.
    data['questions'].append(data['questions'].pop(0))
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_router_question_options_must_not_declare_weights(tmp_path):
    data = _config_with_router()
    data['questions'][0]['options'][0]['weights'] = {'accountant': 1}
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_router_question_options_must_cover_both_audiences(tmp_path):
    data = _config_with_router()
    data['questions'][0]['options'][1]['audience_value'] = 'individual'  # both now 'individual'
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_router_question_option_bad_audience_value_raises(tmp_path):
    data = _config_with_router()
    data['questions'][0]['options'][0]['audience_value'] = 'not-a-real-audience'
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_router_question_must_not_declare_audience(tmp_path):
    data = _config_with_router()
    data['questions'][0]['audience'] = ['individual']
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_router_question_must_not_be_short_text(tmp_path):
    data = _config_with_router()
    data['questions'][0] = {
        'id': 'respondent_type', 'type': 'short_text', 'prompt': 'Individual or organisation?',
    }
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_respondent_type_question_must_reference_an_existing_first_question(tmp_path):
    data = _config_with_router()
    data['respondent_type_question'] = 'not_the_first_question'
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_question_audience_field_must_be_valid_list(tmp_path):
    data = _config_with_router()
    data['questions'][1]['audience'] = 'individual'  # must be a list, not a bare string
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_question_audience_field_rejects_unknown_value(tmp_path):
    data = _config_with_router()
    data['questions'][1]['audience'] = ['not-a-real-audience']
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_survey_without_router_question_still_loads(tmp_path):
    """respondent_type_question is optional — backward compatible with
    surveys (like the route-test fixture) that don't branch by audience."""
    config = load_survey(_write_yaml(tmp_path, _base_config()))
    assert config.get('respondent_type_question') is None


# ---------------------------------------------------------------------------
# effective_questions
# ---------------------------------------------------------------------------

def test_effective_questions_with_no_router_returns_everything(tmp_path):
    from app.survey.loader import effective_questions

    config = load_survey(_write_yaml(tmp_path, _base_config()))
    assert [q['id'] for q in effective_questions(config, None)] == \
        [q['id'] for q in config['questions']]


def test_effective_questions_before_routing_excludes_audience_tagged_questions(tmp_path):
    from app.survey.loader import effective_questions

    data = _config_with_router()
    data['questions'][1]['audience'] = ['organisation']
    config = load_survey(_write_yaml(tmp_path, data))

    ids = [q['id'] for q in effective_questions(config, None)]
    assert 'respondent_type' in ids
    assert 'q_single' not in ids   # organisation-only, not yet routed
    assert 'q_short_text' in ids   # untagged — shared


def test_effective_questions_filters_by_audience(tmp_path):
    from app.survey.loader import effective_questions

    data = _config_with_router()
    data['questions'][1]['audience'] = ['organisation']
    config = load_survey(_write_yaml(tmp_path, data))

    org_ids = [q['id'] for q in effective_questions(config, 'organisation')]
    ind_ids = [q['id'] for q in effective_questions(config, 'individual')]
    assert 'q_single' in org_ids
    assert 'q_single' not in ind_ids
    assert 'respondent_type' in org_ids and 'respondent_type' in ind_ids


# ---------------------------------------------------------------------------
# New question types (backlog #0003): triangle, multi_exact, grid; the
# `output` schema tag; the optional `label_organisation` option field; and
# the `profile_question` top-level key.
# ---------------------------------------------------------------------------

def _grid_question(qid='profile_grid'):
    return {
        'id': qid,
        'type': 'grid',
        'prompt': 'Where would you like to act, and how?',
        'x_axis': {
            'label': 'Where would you like to act?',
            'options': ['Internal', 'Sector', 'Society'],
        },
        'y_axis': {
            'label': 'What approach would you like to use?',
            'options': ['Create a stage', 'Implement', 'Develop'],
        },
        'cells': [
            {'x': 0, 'y': 2, 'persona': 'developer'},
            {'x': 1, 'y': 2, 'persona': 'advocate'},
            {'x': 2, 'y': 2, 'persona': 'cooperator'},
            {'x': 0, 'y': 1, 'persona': 'implementer'},
            {'x': 1, 'y': 1, 'persona': 'entrepreneur'},
            {'x': 2, 'y': 1, 'persona': 'connector'},
            {'x': 0, 'y': 0, 'persona': 'accountant'},
            {'x': 1, 'y': 0, 'persona': 'communicator'},
            {'x': 2, 'y': 0, 'persona': 'activist'},
        ],
    }


def _triangle_question(qid='q_triangle'):
    return {
        'id': qid,
        'type': 'triangle',
        'prompt': 'Pick a corner',
        'options': [{'label': 'A'}, {'label': 'B'}, {'label': 'C'}],
    }


def _multi_exact_question(qid='q_multi_exact', choose_exactly=2):
    return {
        'id': qid,
        'type': 'multi_exact',
        'choose_exactly': choose_exactly,
        'prompt': 'Pick exactly two',
        'options': [{'label': 'Item 1'}, {'label': 'Item 2'}, {'label': 'Item 3'}, {'label': 'Item 4'}],
    }


def test_valid_grid_question_loads(tmp_path):
    data = _base_config()
    data['questions'].append(_grid_question())
    config = load_survey(_write_yaml(tmp_path, data))
    grid = next(q for q in config['questions'] if q['id'] == 'profile_grid')
    assert len(grid['cells']) == 9
    assert 'options' not in grid


def test_grid_with_missing_axis_options_raises(tmp_path):
    data = _base_config()
    grid = _grid_question()
    grid['x_axis']['options'] = ['Internal', 'Sector']  # only 2, needs 3
    data['questions'].append(grid)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_grid_with_wrong_cell_count_raises(tmp_path):
    data = _base_config()
    grid = _grid_question()
    grid['cells'] = grid['cells'][:-1]  # only 8 cells
    data['questions'].append(grid)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_grid_with_duplicate_cell_coordinate_raises(tmp_path):
    data = _base_config()
    grid = _grid_question()
    grid['cells'][1]['x'] = grid['cells'][0]['x']
    grid['cells'][1]['y'] = grid['cells'][0]['y']
    data['questions'].append(grid)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_grid_with_unknown_cell_persona_raises(tmp_path):
    data = _base_config()
    grid = _grid_question()
    grid['cells'][0]['persona'] = 'not-a-real-persona'
    data['questions'].append(grid)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_grid_with_duplicate_persona_across_cells_raises(tmp_path):
    data = _base_config()
    grid = _grid_question()
    grid['cells'][1]['persona'] = grid['cells'][0]['persona']
    data['questions'].append(grid)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_profile_question_naming_a_non_grid_question_raises(tmp_path):
    data = _base_config()
    data['profile_question'] = 'q_single'  # exists but is type 'single'
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_profile_question_naming_a_missing_question_raises(tmp_path):
    data = _base_config()
    data['profile_question'] = 'does_not_exist'
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_profile_question_naming_a_grid_question_loads(tmp_path):
    data = _base_config()
    data['questions'].append(_grid_question())
    data['profile_question'] = 'profile_grid'
    config = load_survey(_write_yaml(tmp_path, data))
    assert config['profile_question'] == 'profile_grid'


def test_multi_exact_valid_loads(tmp_path):
    data = _base_config()
    data['questions'].append(_multi_exact_question())
    config = load_survey(_write_yaml(tmp_path, data))
    q = next(q for q in config['questions'] if q['id'] == 'q_multi_exact')
    assert q['choose_exactly'] == 2
    assert [opt['index'] for opt in q['options']] == [0, 1, 2, 3]


def test_multi_exact_missing_choose_exactly_raises(tmp_path):
    data = _base_config()
    q = _multi_exact_question()
    del q['choose_exactly']
    data['questions'].append(q)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_multi_exact_non_int_choose_exactly_raises(tmp_path):
    data = _base_config()
    q = _multi_exact_question(choose_exactly='two')
    data['questions'].append(q)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_multi_exact_boolean_choose_exactly_raises(tmp_path):
    """bool is a subclass of int — guard against `choose_exactly: true`."""
    data = _base_config()
    q = _multi_exact_question(choose_exactly=True)
    data['questions'].append(q)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_multi_exact_out_of_range_choose_exactly_raises(tmp_path):
    data = _base_config()
    q = _multi_exact_question(choose_exactly=5)  # only 4 options
    data['questions'].append(q)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_triangle_valid_three_option_loads(tmp_path):
    data = _base_config()
    data['questions'].append(_triangle_question())
    config = load_survey(_write_yaml(tmp_path, data))
    q = next(q for q in config['questions'] if q['id'] == 'q_triangle')
    assert len(q['options']) == 3


def test_triangle_with_two_options_raises(tmp_path):
    data = _base_config()
    q = _triangle_question()
    q['options'] = q['options'][:2]
    data['questions'].append(q)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_triangle_with_four_options_raises(tmp_path):
    data = _base_config()
    q = _triangle_question()
    q['options'].append({'label': 'D'})
    data['questions'].append(q)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_unknown_output_value_raises(tmp_path):
    data = _base_config()
    data['questions'][0]['output'] = 'not-a-real-output'
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_absent_output_is_fine(tmp_path):
    config = load_survey(_write_yaml(tmp_path, _base_config()))
    assert 'output' not in config['questions'][0]


def test_valid_output_value_loads(tmp_path):
    data = _base_config()
    data['questions'][0]['output'] = 'now'
    config = load_survey(_write_yaml(tmp_path, data))
    assert config['questions'][0]['output'] == 'now'


def test_option_with_no_weights_loads_cleanly(tmp_path):
    """Regression guard: `weights` is now optional on single/spectrum/multi/
    triangle/multi_exact options — a missing `weights` must not raise."""
    data = _base_config()
    del data['questions'][0]['options'][0]['weights']
    config = load_survey(_write_yaml(tmp_path, data))
    q = next(q for q in config['questions'] if q['id'] == 'q_single')
    assert 'weights' not in q['options'][0]


def test_non_string_label_organisation_raises(tmp_path):
    data = _base_config()
    data['questions'][0]['options'][0]['label_organisation'] = 123
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_empty_label_organisation_raises(tmp_path):
    data = _base_config()
    data['questions'][0]['options'][0]['label_organisation'] = ''
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_valid_label_organisation_loads(tmp_path):
    data = _base_config()
    data['questions'][0]['options'][0]['label_organisation'] = 'We prefer this wording'
    config = load_survey(_write_yaml(tmp_path, data))
    q = next(q for q in config['questions'] if q['id'] == 'q_single')
    assert q['options'][0]['label_organisation'] == 'We prefer this wording'


# ---------------------------------------------------------------------------
# Option 'score' / 'unlabelled' fields, and the top-level 'innovation_curve'
# construct (backlog #0002 — Rogers' innovation-curve scoring)
# ---------------------------------------------------------------------------

def test_valid_option_score_loads(tmp_path):
    data = _base_config()
    data['questions'][0]['options'][0]['score'] = 1
    config = load_survey(_write_yaml(tmp_path, data))
    q = next(q for q in config['questions'] if q['id'] == 'q_single')
    assert q['options'][0]['score'] == 1


def test_non_int_option_score_raises(tmp_path):
    data = _base_config()
    data['questions'][0]['options'][0]['score'] = 'one'
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_boolean_option_score_raises(tmp_path):
    """bool is a subclass of int — guard against `score: true`."""
    data = _base_config()
    data['questions'][0]['options'][0]['score'] = True
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_valid_option_unlabelled_loads(tmp_path):
    data = _base_config()
    data['questions'][0]['options'][0]['unlabelled'] = True
    config = load_survey(_write_yaml(tmp_path, data))
    q = next(q for q in config['questions'] if q['id'] == 'q_single')
    assert q['options'][0]['unlabelled'] is True


def test_non_boolean_option_unlabelled_raises(tmp_path):
    data = _base_config()
    data['questions'][0]['options'][0]['unlabelled'] = 'yes'
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def _innovation_curve_construct():
    return {
        'persona_modifiers': {'accountant': 0, 'developer': 4},
        'bands': [
            {
                'name': 'Laggards', 'min': 0, 'max': 2, 'colour': '#c0392b',
                'tagline': 'Laggard tagline', 'description': 'Laggard description',
            },
            {
                'name': 'Innovators', 'min': 3, 'max': 20, 'colour': '#2e7d32',
                'tagline': 'Innovator tagline', 'description': 'Innovator description',
            },
        ],
    }


def test_absent_innovation_curve_is_valid(tmp_path):
    config = load_survey(_write_yaml(tmp_path, _base_config()))
    assert config.get('innovation_curve') is None


def test_valid_innovation_curve_loads(tmp_path):
    data = _base_config()
    data['innovation_curve'] = _innovation_curve_construct()
    config = load_survey(_write_yaml(tmp_path, data))
    assert config['innovation_curve']['bands'][0]['name'] == 'Laggards'


def test_innovation_curve_unknown_persona_modifier_key_raises(tmp_path):
    data = _base_config()
    ic = _innovation_curve_construct()
    ic['persona_modifiers']['not-a-real-persona'] = 1
    data['innovation_curve'] = ic
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_innovation_curve_non_number_modifier_raises(tmp_path):
    data = _base_config()
    ic = _innovation_curve_construct()
    ic['persona_modifiers']['accountant'] = 'zero'
    data['innovation_curve'] = ic
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_innovation_curve_empty_bands_raises(tmp_path):
    data = _base_config()
    ic = _innovation_curve_construct()
    ic['bands'] = []
    data['innovation_curve'] = ic
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


@pytest.mark.parametrize('missing_field', ['name', 'min', 'max', 'colour'])
def test_innovation_curve_band_missing_field_raises(tmp_path, missing_field):
    data = _base_config()
    ic = _innovation_curve_construct()
    del ic['bands'][0][missing_field]
    data['innovation_curve'] = ic
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_innovation_curve_band_non_int_min_max_raises(tmp_path):
    data = _base_config()
    ic = _innovation_curve_construct()
    ic['bands'][0]['min'] = 'zero'
    data['innovation_curve'] = ic
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_real_survey_loads_the_innovation_curve_construct():
    config = load_survey(REAL_SURVEY_PATH)
    assert config['innovation_curve']['persona_modifiers']['accountant'] == 0
    assert config['innovation_curve']['bands'][0]['name'] == 'Laggards'
