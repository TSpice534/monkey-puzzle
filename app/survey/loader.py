"""Load, validate and normalise `content/survey.yaml`.

This is the single source of truth for questions, personas and scoring
config, owned by Rob and Andrew. The engine here only knows the *shape*
the YAML must conform to — it never hardcodes survey content.
"""
import yaml
from flask import current_app

_VALID_TYPES = {'spectrum', 'single', 'multi', 'short_text', 'triangle', 'multi_exact', 'multi_range', 'grid'}
_VALID_AUDIENCES = {'individual', 'organisation'}
_VALID_OUTPUTS = {'innovation_curve', 'now', 'next', 'profile_direct', 'why'}
_TYPES_WITH_OPTIONS = {'spectrum', 'single', 'multi', 'triangle', 'multi_exact', 'multi_range'}

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
        _validate_innovation_curve(raw)
        _validate_now_next(raw)
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
        desc_org = persona.get('description_organisation')
        if desc_org is not None and (not isinstance(desc_org, str) or not desc_org):
            raise SurveyConfigError(
                f"persona '{persona_id}' field 'description_organisation', if present, must be a non-empty string"
            )
        icon = persona.get('icon')
        if icon is not None and (not isinstance(icon, str) or not icon):
            raise SurveyConfigError(
                f"persona '{persona_id}' field 'icon', if present, must be a non-empty string"
            )
        for rel in ('natural_allies', 'friends', 'necessity'):
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

    # `respondent_type_question` is optional (the small test fixture doesn't
    # use it) — when present, it names the id of a routing question that
    # must be first, whose options set `submission.audience` instead of
    # scoring personas. See `effective_questions()` for how `audience`-
    # tagged questions get filtered per submission.
    router_id = raw.get('respondent_type_question')
    if router_id is not None:
        if not isinstance(router_id, str) or not router_id:
            raise SurveyConfigError("survey.yaml 'respondent_type_question' must be a non-empty string")
        if questions[0].get('id') != router_id:
            raise SurveyConfigError(
                "survey.yaml 'respondent_type_question' must be the id of the first entry in 'questions'"
            )

    # `profile_question` is optional — when present, it names the id of the
    # interactive grid question that directly resolves the winning persona
    # (see `app/survey/persona.py::resolve_profile_persona`).
    profile_id = raw.get('profile_question')
    if profile_id is not None and (not isinstance(profile_id, str) or not profile_id):
        raise SurveyConfigError("survey.yaml 'profile_question' must be a non-empty string")

    valid_persona_ids = set(raw['personas'].keys())
    seen_ids = set()
    question_types = {}
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

        is_router = qid == router_id

        audience = q.get('audience')
        if audience is not None:
            if is_router:
                raise SurveyConfigError(f"router question '{qid}' must not declare 'audience' — it sets it")
            if (not isinstance(audience, list) or not audience
                    or not set(audience) <= _VALID_AUDIENCES):
                raise SurveyConfigError(
                    f"question '{qid}' field 'audience' must be a non-empty list drawn from "
                    f'{sorted(_VALID_AUDIENCES)}'
                )

        qtype = q.get('type')
        if qtype not in _VALID_TYPES:
            raise SurveyConfigError(
                f"question '{qid}' has invalid type '{qtype}'; must be one of "
                f'{sorted(_VALID_TYPES)}'
            )
        question_types[qid] = qtype

        output = q.get('output')
        if output is not None and output not in _VALID_OUTPUTS:
            raise SurveyConfigError(
                f"question '{qid}' has invalid 'output' value '{output}'; must be one of "
                f'{sorted(_VALID_OUTPUTS)}'
            )

        if qtype == 'short_text':
            if q.get('options'):
                raise SurveyConfigError(f"question '{qid}' is type short_text and must not have 'options'")
            if is_router:
                raise SurveyConfigError(f"router question '{qid}' must not be type short_text")
            continue

        if qtype == 'grid':
            if is_router:
                raise SurveyConfigError(f"router question '{qid}' must not be type grid")
            if q.get('options'):
                raise SurveyConfigError(f"question '{qid}' is type grid and must not have top-level 'options'")
            _validate_grid_question(q, valid_persona_ids)
            continue

        options = q.get('options')
        if qtype == 'triangle':
            if not isinstance(options, list) or len(options) != 3:
                raise SurveyConfigError(f"question '{qid}' is type triangle and must have exactly 3 'options'")
        else:
            if not isinstance(options, list) or len(options) < 2:
                raise SurveyConfigError(f"question '{qid}' must have at least 2 'options'")

        if qtype == 'multi_exact':
            choose_exactly = q.get('choose_exactly')
            if (
                not isinstance(choose_exactly, int)
                or isinstance(choose_exactly, bool)
                or not (1 <= choose_exactly <= len(options))
            ):
                raise SurveyConfigError(
                    f"question '{qid}' is type multi_exact and must have an integer 'choose_exactly' "
                    f'between 1 and the number of options'
                )

        if qtype == 'multi_range':
            choose_min = q.get('choose_min')
            choose_max = q.get('choose_max')
            if (
                not isinstance(choose_min, int) or isinstance(choose_min, bool)
                or not isinstance(choose_max, int) or isinstance(choose_max, bool)
                or not (1 <= choose_min <= choose_max <= len(options))
            ):
                raise SurveyConfigError(
                    f"question '{qid}' is type multi_range and must have integer 'choose_min'/'choose_max' "
                    'with 1 <= choose_min <= choose_max <= number of options'
                )
            instructions = q.get('instructions')
            if instructions is not None and (not isinstance(instructions, str) or not instructions):
                raise SurveyConfigError(
                    f"question '{qid}' is type multi_range and 'instructions', if present, "
                    'must be a non-empty string'
                )

        router_audience_values = set()
        for i, opt in enumerate(options):
            if not isinstance(opt, dict) or not opt.get('label'):
                raise SurveyConfigError(f"question '{qid}' option {i} must have a non-empty 'label'")

            label_organisation = opt.get('label_organisation')
            if label_organisation is not None and (
                not isinstance(label_organisation, str) or not label_organisation
            ):
                raise SurveyConfigError(
                    f"question '{qid}' option {i} 'label_organisation', if present, must be a non-empty string"
                )

            score = opt.get('score')
            if score is not None and (not isinstance(score, int) or isinstance(score, bool)):
                raise SurveyConfigError(
                    f"question '{qid}' option {i} 'score', if present, must be an integer"
                )

            unlabelled = opt.get('unlabelled')
            if unlabelled is not None and not isinstance(unlabelled, bool):
                raise SurveyConfigError(
                    f"question '{qid}' option {i} 'unlabelled', if present, must be a boolean"
                )

            statement_phrase = opt.get('statement_phrase')
            if statement_phrase is not None and (not isinstance(statement_phrase, str) or not statement_phrase):
                raise SurveyConfigError(
                    f"question '{qid}' option {i} 'statement_phrase', if present, must be a non-empty string"
                )
            statement_phrase_organisation = opt.get('statement_phrase_organisation')
            if statement_phrase_organisation is not None and (
                not isinstance(statement_phrase_organisation, str) or not statement_phrase_organisation
            ):
                raise SurveyConfigError(
                    f"question '{qid}' option {i} 'statement_phrase_organisation', if present, must be a non-empty string"
                )

            if is_router:
                audience_value = opt.get('audience_value')
                if audience_value not in _VALID_AUDIENCES:
                    raise SurveyConfigError(
                        f"router question '{qid}' option {i} must set 'audience_value' to one of "
                        f'{sorted(_VALID_AUDIENCES)}'
                    )
                if opt.get('weights'):
                    raise SurveyConfigError(
                        f"router question '{qid}' option {i} must not declare 'weights' — "
                        'it routes, it does not score'
                    )
                router_audience_values.add(audience_value)
                continue

            weights = opt.get('weights')
            if weights is not None:
                if not isinstance(weights, dict):
                    raise SurveyConfigError(f"question '{qid}' option {i} 'weights', if present, must be a mapping")
                for persona_id, weight in weights.items():
                    if persona_id not in valid_persona_ids:
                        raise SurveyConfigError(
                            f"question '{qid}' option {i} weights reference unknown persona id '{persona_id}'"
                        )
                    if not isinstance(weight, (int, float)) or isinstance(weight, bool):
                        raise SurveyConfigError(
                            f"question '{qid}' option {i} weight for '{persona_id}' must be a number"
                        )

        if is_router and router_audience_values != _VALID_AUDIENCES:
            raise SurveyConfigError(
                f"router question '{qid}' options must cover each of {sorted(_VALID_AUDIENCES)} at least once"
            )

    if profile_id is not None:
        if profile_id not in question_types:
            raise SurveyConfigError(
                f"survey.yaml 'profile_question' references unknown question id '{profile_id}'"
            )
        if question_types[profile_id] != 'grid':
            raise SurveyConfigError(
                f"survey.yaml 'profile_question' must name a question of type 'grid', "
                f"but '{profile_id}' is type '{question_types[profile_id]}'"
            )


def _validate_grid_question(q, valid_persona_ids):
    qid = q['id']

    for axis_name in ('x_axis', 'y_axis'):
        axis = q.get(axis_name)
        if not isinstance(axis, dict) or not axis.get('label'):
            raise SurveyConfigError(f"question '{qid}' '{axis_name}' must be a mapping with a non-empty 'label'")
        axis_options = axis.get('options')
        if (
            not isinstance(axis_options, list)
            or len(axis_options) != 3
            or not all(isinstance(o, str) and o for o in axis_options)
        ):
            raise SurveyConfigError(
                f"question '{qid}' '{axis_name}.options' must be a list of exactly 3 non-empty strings"
            )

    cells = q.get('cells')
    if not isinstance(cells, list) or len(cells) != 9:
        raise SurveyConfigError(f"question '{qid}' 'cells' must be a list of exactly 9 entries")

    seen_coords = set()
    seen_personas = set()
    for i, cell in enumerate(cells):
        if not isinstance(cell, dict):
            raise SurveyConfigError(f"question '{qid}' cell {i} must be a mapping")
        x, y, persona_id = cell.get('x'), cell.get('y'), cell.get('persona')
        if (
            not isinstance(x, int) or isinstance(x, bool) or not (0 <= x <= 2)
            or not isinstance(y, int) or isinstance(y, bool) or not (0 <= y <= 2)
        ):
            raise SurveyConfigError(f"question '{qid}' cell {i} must have integer 'x' and 'y' in 0..2")
        if persona_id not in valid_persona_ids:
            raise SurveyConfigError(f"question '{qid}' cell {i} references unknown persona id '{persona_id}'")
        coord = (x, y)
        if coord in seen_coords:
            raise SurveyConfigError(f"question '{qid}' has duplicate cell coordinate {coord}")
        seen_coords.add(coord)
        if persona_id in seen_personas:
            raise SurveyConfigError(f"question '{qid}' has duplicate persona '{persona_id}' across cells")
        seen_personas.add(persona_id)

    # All 9 (x, y) combos must be present exactly once (no gaps).
    expected_coords = {(x, y) for x in range(3) for y in range(3)}
    if seen_coords != expected_coords:
        raise SurveyConfigError(f"question '{qid}' 'cells' must cover every (x, y) combo in 0..2 exactly once")


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


def _validate_innovation_curve(raw):
    """Optional top-level `innovation_curve` construct (backlog #0002) —
    persona modifiers + Rogers-curve bands for `resolve_innovation_curve`.
    Absent is valid (the small test fixtures have no innovation curve); the
    scored questions themselves aren't re-listed here — the aggregation
    derives them from `output == 'innovation_curve'`."""
    ic = raw.get('innovation_curve')
    if ic is None:
        return

    if not isinstance(ic, dict):
        raise SurveyConfigError("survey.yaml 'innovation_curve' must be a mapping")

    valid_persona_ids = set(raw['personas'].keys())

    modifiers = ic.get('persona_modifiers')
    if not isinstance(modifiers, dict):
        raise SurveyConfigError("survey.yaml 'innovation_curve.persona_modifiers' must be a mapping")
    for persona_id, modifier in modifiers.items():
        if persona_id not in valid_persona_ids:
            raise SurveyConfigError(
                f"survey.yaml 'innovation_curve.persona_modifiers' references unknown persona id '{persona_id}'"
            )
        if not isinstance(modifier, (int, float)) or isinstance(modifier, bool):
            raise SurveyConfigError(
                f"survey.yaml 'innovation_curve.persona_modifiers' value for '{persona_id}' must be a number"
            )

    bands = ic.get('bands')
    if not isinstance(bands, list) or not bands:
        raise SurveyConfigError("survey.yaml 'innovation_curve.bands' must be a non-empty list")
    for i, band in enumerate(bands):
        if not isinstance(band, dict):
            raise SurveyConfigError(f"survey.yaml 'innovation_curve.bands' entry {i} must be a mapping")
        if not band.get('name') or not isinstance(band['name'], str):
            raise SurveyConfigError(f"survey.yaml 'innovation_curve.bands' entry {i} must have a non-empty string 'name'")
        band_min, band_max = band.get('min'), band.get('max')
        if (
            not isinstance(band_min, int) or isinstance(band_min, bool)
            or not isinstance(band_max, int) or isinstance(band_max, bool)
            or band_min > band_max
        ):
            raise SurveyConfigError(
                f"survey.yaml 'innovation_curve.bands' entry {i} must have integer 'min' <= 'max'"
            )
        if not band.get('colour') or not isinstance(band['colour'], str):
            raise SurveyConfigError(f"survey.yaml 'innovation_curve.bands' entry {i} must have a non-empty string 'colour'")
        for field in ('tagline', 'description'):
            if not band.get(field) or not isinstance(band[field], str):
                raise SurveyConfigError(
                    f"survey.yaml 'innovation_curve.bands' entry {i} must have a non-empty string '{field}'"
                )


def _validate_now_next(raw):
    """Optional top-level `now_next` construct (backlog #0007) — the two
    Now/Next narrative statement templates for `resolve_now_next`. Absent is
    valid (the small test fixtures have no now_next); placeholder names
    aren't cross-checked against question ids here — resolution is
    defensive (missing/unknown placeholder -> that statement renders as
    None), same spirit as innovation_curve not re-listing its scored
    questions."""
    nn = raw.get('now_next')
    if nn is None:
        return

    if not isinstance(nn, dict):
        raise SurveyConfigError("survey.yaml 'now_next' must be a mapping")

    for field in ('now', 'next'):
        if not nn.get(field) or not isinstance(nn[field], str):
            raise SurveyConfigError(f"survey.yaml 'now_next' must have a non-empty string '{field}'")

    for field in ('now_organisation', 'next_organisation'):
        value = nn.get(field)
        if value is not None and (not isinstance(value, str) or not value):
            raise SurveyConfigError(
                f"survey.yaml 'now_next' field '{field}', if present, must be a non-empty string"
            )


def _normalise(raw):
    for persona_id, persona in raw['personas'].items():
        persona['id'] = persona_id
        persona.setdefault('natural_allies', [])
        persona.setdefault('friends', [])
        persona.setdefault('necessity', [])
        persona.setdefault('case_studies', [])
        persona.setdefault('resources', [])

    for q in raw['questions']:
        if q['type'] in _TYPES_WITH_OPTIONS:
            for index, opt in enumerate(q['options']):
                opt['index'] = index

    return raw


def effective_questions(survey: dict, audience: str = None) -> list:
    """The questions a submission with the given `audience` ('individual',
    'organisation', or None if not yet routed) should see, in order.

    The router question (if any) is always included. A question tagged with
    `audience: [...]` is only included when `audience` is in that list —
    so before the router question is answered (`audience` is None), only
    untagged (shared) questions are reachable; audience-specific content is
    inaccessible until the respondent-type question routes them.
    """
    router_id = survey.get('respondent_type_question')
    result = []
    for q in survey['questions']:
        if q['id'] == router_id:
            result.append(q)
            continue
        tags = q.get('audience')
        if not tags or audience in tags:
            result.append(q)
    return result


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
