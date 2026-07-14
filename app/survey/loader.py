"""Load, validate and normalise `content/survey.yaml`.

This is the single source of truth for questions, personas and scoring
config, owned by Rob and Andrew. The engine here only knows the *shape*
the YAML must conform to — it never hardcodes survey content.
"""
import yaml
from flask import current_app

_VALID_TYPES = {'spectrum', 'single', 'multi', 'short_text'}

_cache = {}


class SurveyConfigError(Exception):
    """Raised when content/survey.yaml fails to load or validate."""


def load_survey(path: str) -> dict:
    """Read, validate and normalise the YAML at `path`. Raises SurveyConfigError."""
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            raw = yaml.safe_load(fh)
    except FileNotFoundError as exc:
        raise SurveyConfigError(f"survey.yaml not found at '{path}'") from exc
    except yaml.YAMLError as exc:
        raise SurveyConfigError(f"survey.yaml is not valid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise SurveyConfigError('survey.yaml must be a mapping at the top level')

    try:
        _validate_top_level(raw)
        _validate_personas(raw)
        _validate_questions(raw)
        _validate_scoring(raw)
        return _normalise(raw)
    except SurveyConfigError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        # Defensive: turn any schema-shape surprise we didn't anticipate into
        # a SurveyConfigError rather than letting it bubble up as a raw
        # KeyError/TypeError/ValueError.
        raise SurveyConfigError(f'survey.yaml failed validation: {exc}') from exc


def _validate_top_level(raw):
    for key in ('meta', 'personas', 'questions', 'scoring'):
        if key not in raw:
            raise SurveyConfigError(f"survey.yaml is missing required top-level key '{key}'")


def _validate_personas(raw):
    personas = raw['personas']
    if not isinstance(personas, dict) or not personas:
        raise SurveyConfigError("survey.yaml 'personas' must be a non-empty mapping")

    meta = raw.get('meta') or {}
    expected_count = meta.get('personas_count')
    if not isinstance(expected_count, int):
        raise SurveyConfigError("survey.yaml 'meta.personas_count' must be present and an integer")
    if len(personas) != expected_count:
        raise SurveyConfigError(
            f"survey.yaml declares meta.personas_count={expected_count} "
            f"but 'personas' has {len(personas)} entries"
        )

    valid_ids = set(personas.keys())
    for persona_id, persona in personas.items():
        if not isinstance(persona, dict):
            raise SurveyConfigError(f"persona '{persona_id}' must be a mapping")
        for field in ('name', 'tagline', 'description'):
            if not persona.get(field):
                raise SurveyConfigError(f"persona '{persona_id}' is missing a non-empty '{field}'")
        for rel in ('brethren', 'besties', 'battlers'):
            refs = persona.get(rel, [])
            if not isinstance(refs, list):
                raise SurveyConfigError(f"persona '{persona_id}' field '{rel}' must be a list")
            for ref in refs:
                if ref not in valid_ids:
                    raise SurveyConfigError(
                        f"persona '{persona_id}' field '{rel}' references unknown persona id '{ref}'"
                    )
        for coll in ('case_studies', 'resources'):
            items = persona.get(coll, [])
            if not isinstance(items, list):
                raise SurveyConfigError(f"persona '{persona_id}' field '{coll}' must be a list")
            for item in items:
                if not isinstance(item, dict) or not item.get('title') or not item.get('url'):
                    raise SurveyConfigError(
                        f"persona '{persona_id}' field '{coll}' entries must have "
                        "non-empty 'title' and 'url'"
                    )


def _validate_questions(raw):
    questions = raw['questions']
    if not isinstance(questions, list) or not questions:
        raise SurveyConfigError("survey.yaml 'questions' must be a non-empty list")

    valid_persona_ids = set(raw['personas'].keys())
    seen_ids = set()
    for q in questions:
        if not isinstance(q, dict):
            raise SurveyConfigError('every question must be a mapping')

        qid = q.get('id')
        if not qid:
            raise SurveyConfigError("every question must have a non-empty 'id'")
        if qid in seen_ids:
            raise SurveyConfigError(f"duplicate question id '{qid}'")
        seen_ids.add(qid)

        if not q.get('prompt'):
            raise SurveyConfigError(f"question '{qid}' is missing a non-empty 'prompt'")
        if not q.get('dimension'):
            raise SurveyConfigError(f"question '{qid}' is missing a non-empty 'dimension'")

        qtype = q.get('type')
        if qtype not in _VALID_TYPES:
            raise SurveyConfigError(
                f"question '{qid}' has invalid type '{qtype}'; must be one of "
                f'{sorted(_VALID_TYPES)}'
            )

        if qtype == 'short_text':
            if q.get('options'):
                raise SurveyConfigError(f"question '{qid}' is type short_text and must not have 'options'")
            continue

        options = q.get('options')
        if not isinstance(options, list) or len(options) < 2:
            raise SurveyConfigError(f"question '{qid}' must have at least 2 'options'")
        for i, opt in enumerate(options):
            if not isinstance(opt, dict) or not opt.get('label'):
                raise SurveyConfigError(f"question '{qid}' option {i} must have a non-empty 'label'")
            weights = opt.get('weights')
            if not isinstance(weights, dict) or not weights:
                raise SurveyConfigError(f"question '{qid}' option {i} must have a non-empty 'weights' mapping")
            for persona_id, weight in weights.items():
                if persona_id not in valid_persona_ids:
                    raise SurveyConfigError(
                        f"question '{qid}' option {i} weights reference unknown persona id '{persona_id}'"
                    )
                if not isinstance(weight, (int, float)) or isinstance(weight, bool):
                    raise SurveyConfigError(
                        f"question '{qid}' option {i} weight for '{persona_id}' must be a number"
                    )


def _validate_scoring(raw):
    scoring = raw['scoring']
    if not isinstance(scoring, dict):
        raise SurveyConfigError("survey.yaml 'scoring' must be a mapping")

    if scoring.get('method') != 'persona_vector':
        raise SurveyConfigError("survey.yaml 'scoring.method' must be 'persona_vector'")

    persona_ids = set(raw['personas'].keys())
    tie_break = scoring.get('tie_break')
    if (
        not isinstance(tie_break, list)
        or len(tie_break) != len(persona_ids)
        or set(tie_break) != persona_ids
    ):
        raise SurveyConfigError(
            "survey.yaml 'scoring.tie_break' must be a permutation of all persona ids"
        )

    for hook in ('equity_modifier', 'rogers_curve'):
        cfg = scoring.get(hook)
        if not isinstance(cfg, dict) or not isinstance(cfg.get('enabled'), bool):
            raise SurveyConfigError(
                f"survey.yaml 'scoring.{hook}' must be a mapping with a boolean 'enabled'"
            )


def _normalise(raw):
    for persona_id, persona in raw['personas'].items():
        persona['id'] = persona_id
        persona.setdefault('brethren', [])
        persona.setdefault('besties', [])
        persona.setdefault('battlers', [])
        persona.setdefault('case_studies', [])
        persona.setdefault('resources', [])

    for q in raw['questions']:
        if q['type'] != 'short_text':
            for index, opt in enumerate(q['options']):
                opt['index'] = index

    return raw


def get_survey() -> dict:
    """Cached accessor. Resolves path from current_app.config['SURVEY_PATH'];
    caches per resolved path. Used by routes."""
    path = current_app.config['SURVEY_PATH']
    if path not in _cache:
        _cache[path] = load_survey(path)
    return _cache[path]


def clear_survey_cache() -> None:
    """Reset the cache (tests call this after swapping SURVEY_PATH)."""
    _cache.clear()
