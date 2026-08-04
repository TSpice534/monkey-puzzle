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
    'accountant', 'implementer', 'inventor', 'architect', 'communicator',
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
                    {'label': 'Option A', 'weights': {'inventor': 2}},
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


def test_real_survey_and_fixtures_have_no_stray_developer_or_advocate_tokens():
    """Regression guard for backlog #0018 (persona id-level rename:
    developer->inventor, advocate->architect). The real survey content, its
    icon assets, and the test fixtures that deliberately mirror the real
    persona set must never re-introduce the old tokens. Deliberately does
    NOT scan tests/*.py itself -- test_sharing.py's inline synthetic
    persona dicts ('developer' / 'The Developer') are arbitrary,
    self-contained placeholder test data unrelated to the real persona set,
    and are explicitly out of scope per the spec."""
    scan_dirs = [
        os.path.join(REPO_ROOT, 'content'),
        os.path.join(REPO_ROOT, 'tests', 'fixtures'),
        os.path.join(REPO_ROOT, 'app', 'static', 'icons'),
    ]
    offenders = []
    for scan_dir in scan_dirs:
        for root, _dirs, files in os.walk(scan_dir):
            for fname in files:
                path = os.path.join(root, fname)
                if 'developer' in fname.lower() or 'advocate' in fname.lower():
                    offenders.append(path)
                    continue
                try:
                    with open(path, 'r', encoding='utf-8') as fh:
                        text = fh.read()
                except (OSError, UnicodeDecodeError):
                    continue
                if 'developer' in text.lower() or 'advocate' in text.lower():
                    offenders.append(path)
    assert offenders == [], f'stray developer/advocate token(s) found in: {offenders}'


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
    data['questions'][0]['options'][0]['weights'] = {'inventor': -2}
    config = load_survey(_write_yaml(tmp_path, data))
    single_q = next(q for q in config['questions'] if q['id'] == 'q_single')
    assert single_q['options'][0]['weights']['inventor'] == -2


def test_editing_a_weight_changes_scoring_result(tmp_path):
    """The data-driven contract: change a weight in the YAML, re-run the same
    answers, and the winning persona should change — no engine change needed."""
    from app.survey.persona import classify_submission

    config = load_survey(_write_yaml(tmp_path, _base_config()))
    answers = {'q_single': 0}  # picks "Option A" -> inventor: 2
    result = classify_submission(answers, config)
    assert result.persona_id == 'inventor'

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
# New question types (backlog #0003): triangle, multi_exact; the `output`
# schema tag; the optional `label_organisation` option field. The
# `profile_matrix` top-level construct (backlog #0017 Part B) is covered in
# its own section further below.
# ---------------------------------------------------------------------------

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


def _multi_range_question(qid='q_multi_range', choose_min=1, choose_max=3):
    return {
        'id': qid,
        'type': 'multi_range',
        'choose_min': choose_min,
        'choose_max': choose_max,
        'prompt': 'Pick between one and three',
        'options': [{'label': 'Item 1'}, {'label': 'Item 2'}, {'label': 'Item 3'}, {'label': 'Item 4'}],
    }


def _profile_questions():
    """The two `type: single` questions a `profile_matrix` construct can
    reference, mirroring the real `profile_approach`/`profile_scope` shape."""
    return [
        {
            'id': 'profile_approach',
            'type': 'single',
            'prompt': 'Complete the following sentence: "I want to..."',
            'options': [
                {'label': 'Create space to address the topic'},
                {'label': 'Work to implement existing solutions'},
                {'label': 'Test new ideas'},
            ],
        },
        {
            'id': 'profile_scope',
            'type': 'single',
            'prompt': 'Where do you want to focus?',
            'options': [
                {'label': 'Within my own organisation'},
                {'label': 'Collaborating within my sector'},
                {'label': 'Creating impact within wider society'},
            ],
        },
    ]


def _profile_matrix_construct():
    return {
        'prompt': 'Finish the following sentence...',
        'sentence_stem': 'I want to',
        'approach_question': 'profile_approach',
        'scope_question': 'profile_scope',
        'cells': [
            {'approach': 0, 'scope': 0, 'persona': 'accountant'},
            {'approach': 0, 'scope': 1, 'persona': 'communicator'},
            {'approach': 0, 'scope': 2, 'persona': 'activist'},
            {'approach': 1, 'scope': 0, 'persona': 'implementer'},
            {'approach': 1, 'scope': 1, 'persona': 'entrepreneur'},
            {'approach': 1, 'scope': 2, 'persona': 'connector'},
            {'approach': 2, 'scope': 0, 'persona': 'inventor'},
            {'approach': 2, 'scope': 1, 'persona': 'architect'},
            {'approach': 2, 'scope': 2, 'persona': 'cooperator'},
        ],
    }


def _config_with_profile_matrix():
    data = _base_config()
    data['questions'].extend(_profile_questions())
    data['profile_matrix'] = _profile_matrix_construct()
    return data


def test_absent_profile_matrix_is_valid(tmp_path):
    config = load_survey(_write_yaml(tmp_path, _base_config()))
    assert config.get('profile_matrix') is None


def test_valid_profile_matrix_loads(tmp_path):
    config = load_survey(_write_yaml(tmp_path, _config_with_profile_matrix()))
    assert len(config['profile_matrix']['cells']) == 9
    assert config['profile_matrix']['approach_question'] == 'profile_approach'
    assert config['profile_matrix']['scope_question'] == 'profile_scope'
    assert config['profile_matrix']['prompt'] == 'Finish the following sentence...'
    assert config['profile_matrix']['sentence_stem'] == 'I want to'


def test_profile_matrix_missing_prompt_raises(tmp_path):
    data = _config_with_profile_matrix()
    del data['profile_matrix']['prompt']
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_profile_matrix_empty_prompt_raises(tmp_path):
    data = _config_with_profile_matrix()
    data['profile_matrix']['prompt'] = ''
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_profile_matrix_missing_sentence_stem_raises(tmp_path):
    data = _config_with_profile_matrix()
    del data['profile_matrix']['sentence_stem']
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_profile_matrix_empty_sentence_stem_raises(tmp_path):
    data = _config_with_profile_matrix()
    data['profile_matrix']['sentence_stem'] = ''
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_profile_matrix_scope_question_not_immediately_after_approach_raises(tmp_path):
    """The combined survey step (loader.survey_steps) depends on
    scope_question following approach_question directly in `questions`."""
    data = _config_with_profile_matrix()
    questions = data['questions']
    approach_pos = next(i for i, q in enumerate(questions) if q['id'] == 'profile_approach')
    scope_pos = next(i for i, q in enumerate(questions) if q['id'] == 'profile_scope')
    assert scope_pos == approach_pos + 1  # sanity: builder starts adjacent
    spacer = _multi_exact_question(qid='q_spacer')
    questions.insert(approach_pos + 1, spacer)  # now approach, spacer, scope
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_profile_matrix_approach_question_referencing_unknown_question_raises(tmp_path):
    data = _config_with_profile_matrix()
    data['profile_matrix']['approach_question'] = 'does_not_exist'
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_profile_matrix_scope_question_referencing_missing_question_raises(tmp_path):
    data = _config_with_profile_matrix()
    data['profile_matrix']['scope_question'] = 'does_not_exist'
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_profile_matrix_question_not_type_single_raises(tmp_path):
    data = _config_with_profile_matrix()
    data['profile_matrix']['approach_question'] = 'q_single'  # exists but has only 2 options
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_profile_matrix_question_with_wrong_option_count_raises(tmp_path):
    data = _config_with_profile_matrix()
    data['questions'][-2]['options'] = data['questions'][-2]['options'][:2]  # profile_approach, only 2
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_profile_matrix_with_wrong_cell_count_raises(tmp_path):
    data = _config_with_profile_matrix()
    data['profile_matrix']['cells'] = data['profile_matrix']['cells'][:-1]  # only 8 cells
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_profile_matrix_with_duplicate_cell_coordinate_raises(tmp_path):
    data = _config_with_profile_matrix()
    data['profile_matrix']['cells'][1]['approach'] = data['profile_matrix']['cells'][0]['approach']
    data['profile_matrix']['cells'][1]['scope'] = data['profile_matrix']['cells'][0]['scope']
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_profile_matrix_with_unknown_cell_persona_raises(tmp_path):
    data = _config_with_profile_matrix()
    data['profile_matrix']['cells'][0]['persona'] = 'not-a-real-persona'
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_profile_matrix_cell_referencing_pre_rename_persona_id_raises(tmp_path):
    """Failure case for backlog #0018: `personas` now only defines `inventor`
    (post-rename), so a leftover/missed reference to the old id `developer`
    anywhere else in the config -- e.g. a profile_matrix cell some other file
    forgot to update -- must be caught as a config error, not silently
    misroute or crash later. This is the safety net the spec relies on to
    catch any missed rename spot."""
    data = _config_with_profile_matrix()
    data['profile_matrix']['cells'][0]['persona'] = 'developer'  # old id, no longer a real persona
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_profile_matrix_with_duplicate_persona_across_cells_raises(tmp_path):
    data = _config_with_profile_matrix()
    data['profile_matrix']['cells'][1]['persona'] = data['profile_matrix']['cells'][0]['persona']
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


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


def test_multi_range_valid_loads(tmp_path):
    data = _base_config()
    data['questions'].append(_multi_range_question())
    config = load_survey(_write_yaml(tmp_path, data))
    q = next(q for q in config['questions'] if q['id'] == 'q_multi_range')
    assert q['choose_min'] == 1
    assert q['choose_max'] == 3
    assert [opt['index'] for opt in q['options']] == [0, 1, 2, 3]


def test_multi_range_missing_choose_min_raises(tmp_path):
    data = _base_config()
    q = _multi_range_question()
    del q['choose_min']
    data['questions'].append(q)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_multi_range_missing_choose_max_raises(tmp_path):
    data = _base_config()
    q = _multi_range_question()
    del q['choose_max']
    data['questions'].append(q)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_multi_range_non_int_choose_min_raises(tmp_path):
    data = _base_config()
    q = _multi_range_question(choose_min='two')
    data['questions'].append(q)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_multi_range_non_int_choose_max_raises(tmp_path):
    data = _base_config()
    q = _multi_range_question(choose_max='two')
    data['questions'].append(q)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_multi_range_boolean_choose_min_raises(tmp_path):
    """bool is a subclass of int — guard against `choose_min: true`."""
    data = _base_config()
    q = _multi_range_question(choose_min=True)
    data['questions'].append(q)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_multi_range_boolean_choose_max_raises(tmp_path):
    """bool is a subclass of int — guard against `choose_max: true`."""
    data = _base_config()
    q = _multi_range_question(choose_max=True)
    data['questions'].append(q)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_multi_range_reversed_min_max_raises(tmp_path):
    data = _base_config()
    q = _multi_range_question(choose_min=3, choose_max=1)
    data['questions'].append(q)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_multi_range_choose_max_out_of_range_raises(tmp_path):
    data = _base_config()
    q = _multi_range_question(choose_max=5)  # only 4 options
    data['questions'].append(q)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_multi_range_choose_min_zero_raises(tmp_path):
    data = _base_config()
    q = _multi_range_question(choose_min=0)
    data['questions'].append(q)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_multi_range_choose_min_equals_choose_max_loads(tmp_path):
    """choose_min == choose_max is a valid boundary (behaves like an exact
    count, but expressed via multi_range rather than multi_exact)."""
    data = _base_config()
    q = _multi_range_question(choose_min=2, choose_max=2)
    data['questions'].append(q)
    config = load_survey(_write_yaml(tmp_path, data))
    loaded = next(q for q in config['questions'] if q['id'] == 'q_multi_range')
    assert loaded['choose_min'] == 2
    assert loaded['choose_max'] == 2


def test_multi_range_choose_max_equals_option_count_loads(tmp_path):
    """choose_max == len(options) is the other valid boundary (upper edge of
    `choose_max <= len(options)`, distinct from the out-of-range case above)."""
    data = _base_config()
    q = _multi_range_question(choose_max=4)  # exactly 4 options
    data['questions'].append(q)
    config = load_survey(_write_yaml(tmp_path, data))
    loaded = next(q for q in config['questions'] if q['id'] == 'q_multi_range')
    assert loaded['choose_max'] == 4


def test_multi_range_empty_instructions_raises(tmp_path):
    data = _base_config()
    q = _multi_range_question()
    q['instructions'] = ''
    data['questions'].append(q)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_multi_range_valid_instructions_loads(tmp_path):
    data = _base_config()
    q = _multi_range_question()
    q['instructions'] = 'Choose up to 3 options.'
    data['questions'].append(q)
    config = load_survey(_write_yaml(tmp_path, data))
    loaded = next(q for q in config['questions'] if q['id'] == 'q_multi_range')
    assert loaded['instructions'] == 'Choose up to 3 options.'


def test_explanation_empty_raises(tmp_path):
    data = _base_config()
    q = _triangle_question()
    q['explanation'] = ''
    data['questions'].append(q)
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_explanation_valid_loads(tmp_path):
    data = _base_config()
    q = _triangle_question()
    q['explanation'] = 'This question is asking you to consider your options.'
    data['questions'].append(q)
    config = load_survey(_write_yaml(tmp_path, data))
    loaded = next(q for q in config['questions'] if q['id'] == 'q_triangle')
    assert loaded['explanation'] == 'This question is asking you to consider your options.'


def test_explanation_empty_raises_on_short_text_question(tmp_path):
    """`short_text` `continue`s early in the validation loop — the
    `explanation` check must still fire because it sits above that
    early-exit, not skip validation for this type."""
    data = _base_config()
    data['questions'][1]['explanation'] = ''  # q_short_text
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_explanation_valid_loads_on_short_text_question(tmp_path):
    data = _base_config()
    data['questions'][1]['explanation'] = 'Anything you would like to add.'
    config = load_survey(_write_yaml(tmp_path, data))
    loaded = next(q for q in config['questions'] if q['id'] == 'q_short_text')
    assert loaded['explanation'] == 'Anything you would like to add.'



# ---------------------------------------------------------------------------
# backlog #0017 Part A — real content/survey.yaml: reworded copy + explanation
# ---------------------------------------------------------------------------

def test_real_survey_space_to_progress_scores_unchanged_and_label_organisation_dropped():
    """The relabel (backlog #0017 Part A) must not have touched the
    underlying innovation-curve scores, and `label_organisation` must be
    genuinely absent from every option on this question (not merely unused
    elsewhere) — the question is audience-neutral now."""
    config = load_survey(REAL_SURVEY_PATH)
    question = next(q for q in config['questions'] if q['id'] == 'space_to_progress')

    assert [opt['score'] for opt in question['options']] == [1, 3, 5, 3, 1]
    assert all('label_organisation' not in opt for opt in question['options'])
    assert [opt['label'] for opt in question['options']] == [
        'Few commitments, lots of capacity',
        'Some commitments, some capacity',
        'Balanced between our commitments and capacity',
        'Little capacity, high level of commitment',
        'No capacity, fully commited',
    ]


def test_real_survey_explanation_present_on_the_four_expected_questions():
    config = load_survey(REAL_SURVEY_PATH)
    by_id = {q['id']: q for q in config['questions']}

    for qid in ('space_to_progress', 'need_most', 'have_enough', 'support_type'):
        assert by_id[qid].get('explanation'), f"'{qid}' should have a non-empty explanation"


def test_real_survey_target_groups_has_no_explanation():
    config = load_survey(REAL_SURVEY_PATH)
    question = next(q for q in config['questions'] if q['id'] == 'target_groups')
    assert question.get('explanation') is None
    assert question['prompt'] == 'Who are you trying to work with?'


def test_real_survey_support_type_prompt_reworded():
    config = load_survey(REAL_SURVEY_PATH)
    question = next(q for q in config['questions'] if q['id'] == 'support_type')
    assert question['prompt'] == 'What type of assistance do you desire?'


def test_real_survey_multiline_explanations_contain_newlines_not_html():
    """The three bulleted explanations must be stored as real newlines (YAML
    block scalars), not raw `<br>` HTML — the template relies on CSS
    `white-space: pre-line` to turn `\\n` into visible line breaks."""
    config = load_survey(REAL_SURVEY_PATH)
    by_id = {q['id']: q for q in config['questions']}

    for qid in ('need_most', 'have_enough', 'support_type'):
        explanation = by_id[qid]['explanation']
        assert '\n' in explanation
        assert '<br>' not in explanation
        assert '<br/>' not in explanation


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


def test_why_output_value_loads(tmp_path):
    """backlog #0015: `output: why` is a plain passthrough answer, no
    top-level construct needed — just an allow-listed tag value."""
    data = _base_config()
    data['questions'][0]['output'] = 'why'
    config = load_survey(_write_yaml(tmp_path, data))
    assert config['questions'][0]['output'] == 'why'


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
# Persona 'icon' field (backlog #0005 — vector icons for persona cards and
# the labelled result grid). Optional non-empty string, mirroring the
# label_organisation checks above.
# ---------------------------------------------------------------------------

def test_non_string_icon_raises(tmp_path):
    data = _base_config()
    data['personas']['accountant']['icon'] = 123
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_empty_icon_raises(tmp_path):
    data = _base_config()
    data['personas']['accountant']['icon'] = ''
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_absent_icon_loads_fine(tmp_path):
    """icon is optional — the fixture builder never sets it, and load_survey
    must not raise or invent a default."""
    config = load_survey(_write_yaml(tmp_path, _base_config()))
    assert config['personas']['accountant'].get('icon') is None


def test_valid_icon_loads(tmp_path):
    data = _base_config()
    data['personas']['accountant']['icon'] = 'icons/accountant.svg'
    config = load_survey(_write_yaml(tmp_path, data))
    assert config['personas']['accountant']['icon'] == 'icons/accountant.svg'


def test_real_survey_every_persona_has_a_non_empty_icon():
    """Guards content completeness: the schema keeps `icon` optional, but the
    real production content/survey.yaml must set one for every persona so
    the card/grid icons actually show up (backlog #0005)."""
    config = load_survey(REAL_SURVEY_PATH)
    for pid in PERSONA_IDS:
        icon = config['personas'][pid].get('icon')
        assert isinstance(icon, str) and icon, f"persona '{pid}' has no non-empty icon"


def test_real_survey_inventor_and_architect_icons_resolve_to_actual_files(app):
    """Edge case named explicitly in the backlog #0018 spec: renaming the
    `icon:` path in survey.yaml without renaming (or renaming without
    updating the path to match) the underlying SVG file fails *silently* --
    `app.survey.icons.persona_icon` swallows the missing-file OSError and
    returns empty Markup, never an error, so this would not surface as a
    loader/test failure any other way. Assert both renamed persona icons
    actually inline non-empty SVG markup against the real static folder,
    and that the old file names are gone from disk."""
    from app.survey.icons import persona_icon

    config = load_survey(REAL_SURVEY_PATH)
    for pid in ('inventor', 'architect'):
        icon_markup = persona_icon(config['personas'][pid])
        assert str(icon_markup).strip(), f"persona '{pid}' icon resolved to empty markup"

    icons_dir = os.path.join(REPO_ROOT, 'app', 'static', 'icons')
    assert os.path.isfile(os.path.join(icons_dir, 'inventor.svg'))
    assert os.path.isfile(os.path.join(icons_dir, 'architect.svg'))
    assert not os.path.exists(os.path.join(icons_dir, 'developer.svg'))
    assert not os.path.exists(os.path.join(icons_dir, 'advocate.svg'))


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
        'persona_modifiers': {'accountant': 0, 'inventor': 4},
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


# ---------------------------------------------------------------------------
# Option 'statement_phrase' / 'statement_phrase_organisation' fields, and the
# top-level 'now_next' construct (backlog #0007 — Now/Next narrative result
# statements). Mirrors the label_organisation / innovation_curve checks above.
# ---------------------------------------------------------------------------

def test_non_string_statement_phrase_raises(tmp_path):
    data = _base_config()
    data['questions'][0]['options'][0]['statement_phrase'] = 123
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_empty_statement_phrase_raises(tmp_path):
    data = _base_config()
    data['questions'][0]['options'][0]['statement_phrase'] = ''
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_valid_statement_phrase_loads(tmp_path):
    data = _base_config()
    data['questions'][0]['options'][0]['statement_phrase'] = 'capacity'
    config = load_survey(_write_yaml(tmp_path, data))
    q = next(q for q in config['questions'] if q['id'] == 'q_single')
    assert q['options'][0]['statement_phrase'] == 'capacity'


def test_non_string_statement_phrase_organisation_raises(tmp_path):
    data = _base_config()
    data['questions'][0]['options'][0]['statement_phrase_organisation'] = 123
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_empty_statement_phrase_organisation_raises(tmp_path):
    data = _base_config()
    data['questions'][0]['options'][0]['statement_phrase_organisation'] = ''
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_valid_statement_phrase_organisation_loads(tmp_path):
    data = _base_config()
    data['questions'][0]['options'][0]['statement_phrase_organisation'] = 'organisational capacity'
    config = load_survey(_write_yaml(tmp_path, data))
    q = next(q for q in config['questions'] if q['id'] == 'q_single')
    assert q['options'][0]['statement_phrase_organisation'] == 'organisational capacity'


def test_absent_statement_phrase_is_valid(tmp_path):
    """statement_phrase(_organisation) is optional — the fixture builder
    never sets it, and load_survey must not raise or invent a default."""
    config = load_survey(_write_yaml(tmp_path, _base_config()))
    assert config['questions'][0]['options'][0].get('statement_phrase') is None


def _now_next_construct():
    return {
        'now': 'Your focus is {topics}.',
        'next': 'You need {need_most}.',
    }


def test_absent_now_next_is_valid(tmp_path):
    config = load_survey(_write_yaml(tmp_path, _base_config()))
    assert config.get('now_next') is None


def test_valid_now_next_loads(tmp_path):
    data = _base_config()
    data['now_next'] = _now_next_construct()
    config = load_survey(_write_yaml(tmp_path, data))
    assert config['now_next']['now'] == 'Your focus is {topics}.'
    assert config['now_next']['next'] == 'You need {need_most}.'


def test_now_next_not_a_mapping_raises(tmp_path):
    data = _base_config()
    data['now_next'] = 'not a mapping'
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


@pytest.mark.parametrize('missing_field', ['now', 'next'])
def test_now_next_missing_required_field_raises(tmp_path, missing_field):
    data = _base_config()
    nn = _now_next_construct()
    del nn[missing_field]
    data['now_next'] = nn
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


@pytest.mark.parametrize('empty_field', ['now', 'next'])
def test_now_next_empty_required_field_raises(tmp_path, empty_field):
    data = _base_config()
    nn = _now_next_construct()
    nn[empty_field] = ''
    data['now_next'] = nn
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_now_next_valid_organisation_overrides_load(tmp_path):
    data = _base_config()
    nn = _now_next_construct()
    nn['now_organisation'] = 'Our focus is {topics}.'
    nn['next_organisation'] = 'We need {need_most}.'
    data['now_next'] = nn
    config = load_survey(_write_yaml(tmp_path, data))
    assert config['now_next']['now_organisation'] == 'Our focus is {topics}.'
    assert config['now_next']['next_organisation'] == 'We need {need_most}.'


def test_now_next_empty_organisation_override_raises(tmp_path):
    data = _base_config()
    nn = _now_next_construct()
    nn['now_organisation'] = ''
    data['now_next'] = nn
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_now_next_non_string_organisation_override_raises(tmp_path):
    data = _base_config()
    nn = _now_next_construct()
    nn['next_organisation'] = 123
    data['now_next'] = nn
    with pytest.raises(SurveyConfigError):
        load_survey(_write_yaml(tmp_path, data))


def test_real_survey_loads_the_now_next_construct():
    config = load_survey(REAL_SURVEY_PATH)
    assert config['now_next']['now'] == (
        'Your current sustainability focus is {topics}, where you feel you have a '
        'good amount of {have_enough} to help achieve your goals.'
    )
    assert config['now_next']['next'] == (
        'In order to progress your ambitions, you are looking for more {need_most}. '
        'This could be achieved by accessing more {support_type} to address this '
        'challenge. In terms of collaboration ambitions, you are keen to engage more '
        '{target_groups}.'
    )
